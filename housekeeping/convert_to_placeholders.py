"""
This module will convert existing rich text fields to placeholders
"""

from cms.models import Placeholder
from cms.models.pluginmodel import CMSPlugin
from cms.plugins.text.models import Text

import django.http as http
from django.db.models import get_model
import django.shortcuts as shortcuts
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.conf import settings

@login_required
def convert(request, slug = "dryrun"):
    # this dictionary store the information for the conversions
    execute=slug
    models_dictionary = {
        "messages": {},                             # a general set of messages for the user
        "modules":  {
            "news_and_events.models": {             # each module containing the models must be represented, like this
                "application": "News & Events",     # this is the human-friendly name of the module
                "models": {                         # a dictionary with each model in that module
                    "NewsArticle": {                # the actual name of the class
                        "fields": [                 # a list of the fields we're working on
                            {                       # a dictionary for each field
                                "old_field": "content",
                                "new_field": "body",                
                                "slot": "body",
                                },
                            ],
                        "model": "News articles",   # the human-friendly name of the model
                        "actions": {},              # an empty dictionary where we we store the results
                        },
                    "Event": {                      # a second model in that module
                        "fields": [                 
                            {                       
                                "old_field": "content",
                                "new_field": "body",                
                                "slot": "body",
                                },
                            ],
                        "model": "Events",
                        "actions": {},
                        },
                    },
                },
            "vacancies_and_studentships.models": {  # and a second module
                "application": "Vacancies & Studentships",
                "models": {
                    "Vacancy": {
                        "fields": [                 
                            {                       
                                "old_field": "description",
                                "new_field": "body",                
                                "slot": "body",
                                },
                            ],
                        "model": "Vacancies",
                        "actions": {},
                        },
                    "Studentship": {
                        "fields": [                 
                            {                       
                                "old_field": "description",
                                "new_field": "body",                
                                "slot": "body",
                                },
                                ],
                        "model": "Studentships",
                        "actions": {},
                        },
                    },
                },
            "publications.models": {                
                "application": "Publications",
                "models": {
                    "Researcher": {
                        "fields": [                 
                            {                       
                                "old_field": "research_synopsis",
                                "new_field": "synopsis_of_research",                
                                "slot": "body",
                                },
                            {                       
                                "old_field": "research_description",
                                "new_field": "description_of_research",                
                                "slot": "body",
                                },
                            ],
                        "model": "Researcher",
                        "actions": {},
                        },
                    },
                },
            },
        }

    # loop over the modules
    for module, module_values in models_dictionary["modules"].items():

        # loop over the models in the module
        for model, model_values in module_values["models"].items():
            
            # mmodel is the human-readable name of the model, used for the report summary
            mmodel = models_dictionary["modules"][module]["models"][model]["model"]
            models_dictionary["messages"][mmodel]={}

            # import the model
            actual_model = getattr(__import__(module, globals(), locals(), module_values["models"], -1), model)
                                            
            # loop over the fields that need converting
            for field in model_values["fields"]:
                print field

                
                old_field = field["old_field"]
                new_field = field["new_field"]
                slot = field["slot"]

                # create a summary report for this field
                models_dictionary["messages"][mmodel][old_field]={}

                try:
                    getattr(actual_model, new_field)
                except AttributeError:
                    message = "field " + new_field + " is missing - check the model and try agin"
                    models_dictionary["messages"][mmodel][old_field]["Error"]=message
                    continue
                    
                junk_content = []   # a record of those items with nothing but <br /> in them
                moved_items =[]     # a record of the items we migrated to placeholders

                # loop over each item in the class
                for item in actual_model.objects.all():

                    old_field_content = getattr(item, old_field)  # the old field we want to convert

                    # first get rid of junk content (change "<br />" to "")
                    if old_field_content == "<br />":
                        old_field_content = ""
                        setattr(item, old_field, "") # item.content = ""
                        if execute == "convert":
                            item.save()
                    
                    # now the serious business of converting the fields
            
                    # if the item lacks a placeholder, create the placeholder and the reference to it
                    if old_field_content and not getattr(item, new_field, None):

                        # check to see if it's worth converting
                        if len(old_field_content) > 60:

                            # create the placeholder
                            placeholder=Placeholder(slot=slot)
                            if execute == "convert":
                                placeholder.save()
        
                            # refer to the placeholder from the item
                            setattr(item, new_field, placeholder)
        
                            # I copied this from one of the test files
                            plugin_base = CMSPlugin(
                                plugin_type='TextPlugin',
                                placeholder=placeholder, 
                                position=1, 
                                language=settings.LANGUAGES[0][0]) # we assume the original field was in the first language
                            plugin_base.insert_at(None, position='last-child', commit=False)
        
                            # create a text plugin
                            plugin = Text(body='')
                            plugin_base.set_base_attr(plugin)
                            plugin.body = getattr(item, old_field)
                            if execute == "convert":
                                plugin.save()
        
                            # set the old field to ""
                            setattr(item, old_field, "")
                            if execute == "convert":
                                item.save()
                                item.status = "Converted to placeholder"
                            else:
                                item.status = "Unconverted"
                                        
                        else:
                            print "too short", old_field_content
                            # this item is so short it must be junk
                            if execute == "convert":
                                setattr(item, old_field, "")
                                item.status = "Junk field - too short; was deleted instead of converted:" + old_field_content
                                item.save()
                            else:    
                                item.status = "Junk field - too short; will be deleted instead of converted:" + old_field_content
                            # make a note that this was a junk item
                            junk_content.append(item)
                                # make a note that we moved this item

                        moved_items.append(item)    
 
                # information about junk content items
                if execute == "convert":
                    message = " ".join((str(len(junk_content)), "junk items not converted items"))
                else:
                    message = " ".join((str(len(junk_content)), "junk items found"))                    

                models_dictionary["messages"][mmodel][old_field]["Junk fields"]=message

                # information about items that have been/need to be converted
                if execute == "convert":
                    message = str(len(moved_items)) + " items were converted to placeholder " + new_field
                else:
                    message = str(len(moved_items)) + " items need to be converted to placeholder " + new_field
            
                models_dictionary["messages"][mmodel][old_field]["Conversions"]=message
            
                # list every item that was copied for the full report
                if execute == "convert":
                    action = "Fields that were copied"
                else:
                    action = "Fields to be copied"
                    
                models_dictionary["modules"][module]["models"][model]["actions"][action]=moved_items
                

    return shortcuts.render_to_response(
        "housekeeping/convert_to_placeholders.html", {
            "execute": execute,
            "converted": models_dictionary,
            },
        RequestContext(request),
        )
