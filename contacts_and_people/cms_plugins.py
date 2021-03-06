from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from models import EntityAutoPageLinkPluginEditor, EntityDirectoryPluginEditor, EntityMembersPluginEditor
from django.utils.translation import ugettext as _

from contacts_and_people.templatetags.entity_tags import work_out_entity
from contacts_and_people.models import Membership

# for autocomplete search
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse

# for tabbed interface
from arkestra_utilities import admin_tabs_extension
from arkestra_utilities.admin import AutocompleteMixin

class EntityAutoPageLinkPluginPublisher(AutocompleteMixin, CMSPluginBase):
    model = EntityAutoPageLinkPluginEditor
    name = _("Entity auto page link")
    render_template = "entity-auto-page-link.html"
    text_enabled = True
 
    # autocomplete fields
    related_search_fields = ['entity',]
    
    def render(self, context, instance, placeholder):

        # get a tuple containing for example:
        # (u'Contacts & people', 'contact', 'contacts_page_menu_title')
        LINK_TUPLE = EntityAutoPageLinkPluginEditor.AUTO_PAGES[instance.link_to]
        kind = LINK_TUPLE[1]
        field_name = LINK_TUPLE[2]
        
        entity = work_out_entity(context, None)
        if entity or instance.entity:
            link = instance.entity.get_related_info_page_url(kind)
            if instance.entity and instance.entity != entity:
                link_title = instance.entity.short_name + ': ' + getattr(instance.entity,field_name)
            else:
                link_title = getattr(instance.entity, field_name)
            if instance.text_override:
                link_title = instance.text_override
            context.update({ 
                'link': link,
                'link_title': link_title,
            })
            return context
    
    def icon_src(self, instance):
        return "/static/plugin_icons/entity_auto_page_link.png"

class EntityDirectoryPluginPublisher(AutocompleteMixin, CMSPluginBase):
    model = EntityDirectoryPluginEditor
    name = _("Directory")
    render_template = "directory.html"
    text_enabled = True
 
    # autocomplete fields
    related_search_fields = ['entity',]

    def icon_src(self, instance):
        return "/static/plugin_icons/entity_directory.png"
        
    def render(self, context, instance, placeholder):
        print "in EntityDirectoryPluginPublisher"
        if instance.entity:
            entity = instance.entity
        else:
            entity = work_out_entity(context, None)
        descendants = entity.get_descendants()
        if descendants:
            # find our base level
            first_level = descendants[0].level
            # filter to maximum sub-level depth    
            if instance.levels:
                maximum_level = first_level + instance.levels
                descendants = descendants.filter(level__lt = maximum_level)
            # apply all the attributes we need to our descendant entities
            for descendant in descendants:
                # reset the level, so that first_level is 0
                descendant.level = descendant.level - first_level
                if descendant.website and (descendant.level < instance.display_descriptions_to_level or instance.display_descriptions_to_level == None):                    
                    descendant.description = descendant.website.get_meta_description()

        context.update({
            'entities': descendants,
            'directory': instance,
        })
        return context


class EntityMembersPluginPublisher(AutocompleteMixin, CMSPluginBase):
    """
    Returns all the memberships in the entity and its descendants; the template groups them by entity"""
    model = EntityMembersPluginEditor
    name = _("Member list")
    render_template = "entity_members_plugin.html"
    text_enabled = True
 
    # autocomplete fields
    related_search_fields = ['entity',]

    def icon_src(self, instance):
        return "/static/plugin_icons/entity_members.png"
           
    def render(self, context, instance, placeholder):
        if instance.entity:
            entity = instance.entity
        else:
            entity = work_out_entity(context, None)
        print "ok so far"

        entities = entity.get_descendants(include_self = True)
        
        memberships = Membership.objects.filter(entity__in = entities).order_by('entity', '-importance_to_entity')

        nest = memberships.values('entity',).distinct().count() > 1 or False
        print nest

        print "returning context"
        context.update({
            'entity': entity,
            'memberships': memberships,
            'nest': nest,
            })
        return context

plugin_pool.register_plugin(EntityDirectoryPluginPublisher)
plugin_pool.register_plugin(EntityMembersPluginPublisher)
plugin_pool.register_plugin(EntityAutoPageLinkPluginPublisher)
