from django.conf.urls import patterns, url

from pulp.server.webservices.views.consumers import (ConsumerBindingsView,
                                                     ConsumerBindingSearchView,
                                                     ConsumerBindingResourceView,
                                                     ConsumerContentActionView,
                                                     ConsumerContentApplicRegenerationView,
                                                     ConsumerContentApplicabilityView,
                                                     ConsumerHistoryView,
                                                     ConsumerProfilesView,
                                                     ConsumerProfileResourceView,
                                                     ConsumerProfileSearchView,
                                                     ConsumerResourceContentApplicRegenerationView,
                                                     ConsumerResourceView,
                                                     ConsumersView,
                                                     UnitInstallSchedulesView,
                                                     ConsumerSearchView,
                                                     UnitInstallScheduleResourceView,
                                                     UnitUninstallSchedulesView,
                                                     UnitUninstallScheduleResourceView,
                                                     UnitUpdateSchedulesView,
                                                     UnitUpdateScheduleResourceView)

from pulp.server.webservices.views import tasks, users, task_groups
from pulp.server.webservices.views.consumer_groups import (ConsumerGroupAssociateActionView,
                                                           ConsumerGroupBindingView,
                                                           ConsumerGroupBindingsView,
                                                           ConsumerGroupContentActionView,
                                                           ConsumerGroupResourceView,
                                                           ConsumerGroupSearchView,
                                                           ConsumerGroupUnassociateActionView,
                                                           ConsumerGroupView)

from pulp.server.webservices.views.content import (
    CatalogResourceView,
    ContentSourceCollectionActionView,
    ContentSourceCollectionView,
    ContentSourceResourceActionView,
    ContentSourceResourceView,
    ContentUnitResourceView,
    ContentUnitsCollectionView,
    ContentUnitSearch,
    ContentUnitUserMetadataResourceView,
    DeleteOrphansActionView,
    OrphanCollectionView,
    OrphanResourceView,
    OrphanTypeSubCollectionView,
    UploadResourceView,
    UploadsCollectionView,
    UploadSegmentResourceView
)

from pulp.server.webservices.views.events import (EventResourceView, EventView)
from pulp.server.webservices.views.permissions import (GrantToRoleView, GrantToUserView,
                                                       PermissionView, RevokeFromRoleView,
                                                       RevokeFromUserView)
from pulp.server.webservices.views.plugins import (DistributorResourceView, DistributorsView,
                                                   ImporterResourceView, ImportersView,
                                                   TypeResourceView, TypesView)
from pulp.server.webservices.views.repo_groups import (
    RepoGroupAssociateView, RepoGroupDistributorResourceView, RepoGroupDistributorsView,
    RepoGroupPublishView, RepoGroupResourceView, RepoGroupSearch, RepoGroupsView,
    RepoGroupUnassociateView
)
from pulp.server.webservices.views.repositories import(
    ContentApplicabilityRegenerationView, RepoDistributorResourceView, RepoDistributorsSearchView,
    RepoDistributorsView, RepoAssociate, RepoImporterResourceView, RepoImportersView,
    RepoImportUpload, RepoPublish, RepoPublishHistory, RepoPublishScheduleResourceView,
    RepoPublishSchedulesView, RepoResourceView, RepoSearch, RepoSync, RepoSyncHistory,
    RepoSyncSchedulesView, RepoSyncScheduleResourceView, RepoUnassociate, RepoUnitSearch, ReposView,
)
from pulp.server.webservices.views.roles import (RoleResourceView, RoleUserView, RoleUsersView,
                                                 RolesView)
from pulp.server.webservices.views.root_actions import LoginView
from pulp.server.webservices.views.status import StatusView


handler404 = 'pulp.server.webservices.views.util.page_not_found'


urlpatterns = patterns('',
    url(r'^v2/actions/login/$', LoginView.as_view(), name='login'), # flake8: noqa
    url(r'^v2/consumer_groups/$', ConsumerGroupView.as_view(), name='consumer_group'),
    url(r'^v2/consumers/$', ConsumersView.as_view(), name='consumers'),
    url(r'^v2/consumers/search/$', ConsumerSearchView.as_view(), name='consumer_search'),
    url(r'^v2/consumers/binding/search/$', ConsumerBindingSearchView.as_view(),
        name='consumer_binding_search'),
    url(r'^v2/consumers/profile/search/$', ConsumerProfileSearchView.as_view(),
        name='consumer_profile_search'),
    url(r'^v2/consumers/(?P<consumer_id>[^/]+)/$',
        ConsumerResourceView.as_view(), name='consumer_resource'),
    url(r'^v2/consumers/(?P<consumer_id>[^/]+)/bindings/$',
        ConsumerBindingsView.as_view(), name='bindings'),
    url(r'^v2/consumers/(?P<consumer_id>[^/]+)/bindings/(?P<repo_id>[^/]+)/$',
        ConsumerBindingsView.as_view(), name='bindings_repo'),
    url(r'^v2/consumers/(?P<consumer_id>[^/]+)/bindings/(?P<repo_id>[^/]+)/(?P<distributor_id>[^/]+)/$',
        ConsumerBindingResourceView.as_view(), name='consumer_binding_resource'),
    url(r'^v2/consumers/(?P<consumer_id>[^/]+)/actions/content/regenerate_applicability/$',
        ConsumerResourceContentApplicRegenerationView.as_view(), name='consumer_appl_regen'),
    url(r'^v2/consumers/(?P<consumer_id>[^/]+)/actions/content/(?P<action>[^/]+)/$',
        ConsumerContentActionView.as_view(), name='consumer_content'),
    url(r'^v2/consumers/(?P<consumer_id>[^/]+)/profiles/$',
        ConsumerProfilesView.as_view(), name='consumer_profiles'),
    url(r'^v2/consumers/(?P<consumer_id>[^/]+)/profiles/(?P<content_type>[^/]+)/$',
        ConsumerProfileResourceView.as_view(), name='consumer_profile_resource'),
    url(r'^v2/consumers/actions/content/regenerate_applicability/$',
        ConsumerContentApplicRegenerationView.as_view(), name='appl_regen'),
    url(r'^v2/consumers/content/applicability/$',
        ConsumerContentApplicabilityView.as_view(), name='consumer_query_appl'),
    url(r'^v2/consumers/(?P<consumer_id>[^/]+)/schedules/content/install/$',
        UnitInstallSchedulesView.as_view(), name='schedule_content_install'),
    url(r'^v2/consumers/(?P<consumer_id>[^/]+)/schedules/content/install/(?P<schedule_id>[^/]+)/$',
        UnitInstallScheduleResourceView.as_view(), name='schedule_content_install_resource'),
    url(r'^v2/consumers/(?P<consumer_id>[^/]+)/schedules/content/update/$',
        UnitUpdateSchedulesView.as_view(), name='schedule_content_update'),
    url(r'^v2/consumers/(?P<consumer_id>[^/]+)/schedules/content/update/(?P<schedule_id>[^/]+)/$',
        UnitUpdateScheduleResourceView.as_view(), name='schedule_content_update_resource'),
    url(r'^v2/consumers/(?P<consumer_id>[^/]+)/schedules/content/uninstall/$',
        UnitUninstallSchedulesView.as_view(), name='schedule_content_uninstall'),
    url(r'^v2/consumers/(?P<consumer_id>[^/]+)/schedules/content/uninstall/(?P<schedule_id>[^/]+)/$',
        UnitUninstallScheduleResourceView.as_view(), name='schedule_content_uninstall_resource'),
    url(r'^v2/consumers/(?P<consumer_id>[^/]+)/history/$',
        ConsumerHistoryView.as_view(), name='consumer_history'),
    url(r'^v2/consumer_groups/search/$',
        ConsumerGroupSearchView.as_view(), name='consumer_group_search'),
    url(r'^v2/consumer_groups/(?P<consumer_group_id>[^/]+)/$',
        ConsumerGroupResourceView.as_view(), name='consumer_group_resource'),
    url(r'^v2/consumer_groups/(?P<consumer_group_id>[^/]+)/actions/associate/$',
        ConsumerGroupAssociateActionView.as_view(), name='consumer_group_associate'),
    url(r'^v2/consumer_groups/(?P<consumer_group_id>[^/]+)/actions/unassociate/$',
        ConsumerGroupUnassociateActionView.as_view(), name='consumer_group_unassociate'),
    url(r'^v2/consumer_groups/(?P<consumer_group_id>[^/]+)/actions/content/(?P<action>[^/]+)/$',
        ConsumerGroupContentActionView.as_view(), name='consumer_group_content'),
    url(r'^v2/consumer_groups/(?P<consumer_group_id>[^/]+)/bindings/$',
        ConsumerGroupBindingsView.as_view(), name='consumer_group_bind'),
    url(r'^v2/consumer_groups/(?P<consumer_group_id>[^/]+)' +
        r'/bindings/(?P<repo_id>[^/]+)/(?P<distributor_id>[^/]+)/$',
        ConsumerGroupBindingView.as_view(), name='consumer_group_unbind'),
    url(r'^v2/content/actions/delete_orphans/$', DeleteOrphansActionView.as_view(),
        name='content_actions_delete_orphans'),
    url(r'^v2/content/catalog/(?P<source_id>[^/]+)/$', CatalogResourceView.as_view(),
        name='content_catalog_resource'),
    url(r'^v2/content/orphans/$', OrphanCollectionView.as_view(), name='content_orphan_collection'),
    url(r'^v2/content/orphans/(?P<content_type>[^/]+)/$', OrphanTypeSubCollectionView.as_view(),
        name='content_orphan_type_subcollection'),
    url(r'^v2/content/orphans/(?P<content_type>[^/]+)/(?P<unit_id>[^/]+)/$',
        OrphanResourceView.as_view(), name='content_orphan_resource'),
    url(r'^v2/content/sources/$',
        ContentSourceCollectionView.as_view(),
        name='content_sources'),
    url(r'^v2/content/sources/action/(?P<action>[^/]+)/$',
        ContentSourceCollectionActionView.as_view(),
        name='content_sources_action'),
    url(r'^v2/content/sources/(?P<source_id>[^/]+)/action/(?P<action>[^/]+)/$',
        ContentSourceResourceActionView.as_view(), name='content_sources_resource_action'),
    url(r'^v2/content/sources/(?P<source_id>[^/]+)/$', ContentSourceResourceView.as_view(),
        name='content_sources_resource'),
    url(r'^v2/content/units/(?P<type_id>[^/]+)/$', ContentUnitsCollectionView.as_view(),
        name='content_units_collection'),
    url(r'^v2/content/units/(?P<type_id>[^/]+)/search/$', ContentUnitSearch.as_view(),
        name='content_unit_search'),
    url(r'^v2/content/units/(?P<type_id>[^/]+)/(?P<unit_id>[^/]+)/$',
        ContentUnitResourceView.as_view(), name='content_unit_resource'),
    url(r'^v2/content/units/(?P<type_id>[^/]+)/(?P<unit_id>[^/]+)/pulp_user_metadata/$',
        ContentUnitUserMetadataResourceView.as_view(), name='content_unit_user_metadata_resource'),
    url(r'^v2/content/uploads/$', UploadsCollectionView.as_view(), name='content_uploads'),
    url(r'^v2/content/uploads/(?P<upload_id>[^/]+)/$', UploadResourceView.as_view(),
        name='content_upload_resource'),
    url(r'^v2/content/uploads/(?P<upload_id>[^/]+)/(?P<offset>[^/]+)/$',
        UploadSegmentResourceView.as_view(), name='content_upload_segment_resource'),
    url(r'^v2/distributors/search/$', RepoDistributorsSearchView.as_view(),
        name='distributor_search'),
    url(r'^v2/events/$', EventView.as_view(), name='events'),
    url(r'^v2/events/(?P<event_listener_id>[^/]+)/$', EventResourceView.as_view(), name='event_resource'),
    url(r'^v2/permissions/$', PermissionView.as_view(), name='permissions'),
    url(r'^v2/permissions/actions/grant_to_role/$', GrantToRoleView.as_view(), name='grant_to_role'),
    url(r'^v2/permissions/actions/grant_to_user/$', GrantToUserView.as_view(), name='grant_to_user'),
    url(r'^v2/permissions/actions/revoke_from_role/$', RevokeFromRoleView.as_view(), name='revoke_from_role'),
    url(r'^v2/permissions/actions/revoke_from_user/$', RevokeFromUserView.as_view(), name='revoke_from_user'),
    url(r'^v2/plugins/distributors/$', DistributorsView.as_view(), name='plugin_distributors'),
    url(r'^v2/plugins/distributors/(?P<distributor_id>[^/]+)/$', DistributorResourceView.as_view(),
        name='plugin_distributor_resource'),
    url(r'^v2/plugins/importers/$', ImportersView.as_view(), name='plugin_importers'),
    url(r'^v2/plugins/importers/(?P<importer_id>[^/]+)/$', ImporterResourceView.as_view(),
        name='plugin_importer_resource'),
    url(r'^v2/plugins/types/$', TypesView.as_view(), name='plugin_types'),
    url(r'^v2/plugins/types/(?P<type_id>[^/]+)/$', TypeResourceView.as_view(),
        name='plugin_type_resource'),
    url(r'^v2/repo_groups/$', RepoGroupsView.as_view(), name='repo_groups'),
    url(r'^v2/repo_groups/search/$', RepoGroupSearch.as_view(), name='repo_group_search'),
    url(r'^v2/repo_groups/(?P<repo_group_id>[^/]+)/$', RepoGroupResourceView.as_view(),
        name='repo_group_resource'),
    url(r'^v2/repo_groups/(?P<repo_group_id>[^/]+)/actions/associate/$',
        RepoGroupAssociateView.as_view(), name='repo_group_associate'),
    url(r'^v2/repo_groups/(?P<repo_group_id>[^/]+)/actions/publish/$',
        RepoGroupPublishView.as_view(), name='repo_group_publish'),
    url(r'^v2/repo_groups/(?P<repo_group_id>[^/]+)/actions/unassociate/$',
        RepoGroupUnassociateView.as_view(), name='repo_group_unassociate'),
    url(r'^v2/repo_groups/(?P<repo_group_id>[^/]+)/distributors/$',
        RepoGroupDistributorsView.as_view(), name='repo_group_distributors'),
    url(r'^v2/repo_groups/(?P<repo_group_id>[^/]+)/distributors/(?P<distributor_id>[^/]+)/$',
        RepoGroupDistributorResourceView.as_view(), name='repo_group_distributor_resource'),
    url(r'^v2/repositories/$', ReposView.as_view(), name='repos'),
    url(r'^v2/repositories/search/$', RepoSearch.as_view(), name='repo_search'),
    url(r'^v2/repositories/actions/content/regenerate_applicability/$',
        ContentApplicabilityRegenerationView.as_view(), name='repo_content_app_regen'),
    url(r'^v2/repositories/(?P<repo_id>[^/]+)/$', RepoResourceView.as_view(), name='repo_resource'),
    url(r'^v2/repositories/(?P<repo_id>[^/]+)/search/units/$', RepoUnitSearch.as_view(), name='repo_unit_search'),
    url(r'^v2/repositories/(?P<repo_id>[^/]+)/importers/$', RepoImportersView.as_view(),
        name='repo_importers'),
    url(r'^v2/repositories/(?P<repo_id>[^/]+)/importers/(?P<importer_id>[^/]+)/$',
        RepoImporterResourceView.as_view(), name='repo_importer_resource'),
    url(r'^v2/repositories/(?P<repo_id>[^/]+)/importers/(?P<importer_id>[^/]+)/schedules/sync/$',
        RepoSyncSchedulesView.as_view(), name='repo_sync_schedules'),
    url(r'^v2/repositories/(?P<repo_id>[^/]+)/importers/(?P<importer_id>[^/]+)/schedules/sync/(?P<schedule_id>[^/]+)/$',
        RepoSyncScheduleResourceView.as_view(), name='repo_sync_schedule_resource'),
    url(r'^v2/repositories/(?P<repo_id>[^/]+)/distributors/$', RepoDistributorsView.as_view(),
        name='repo_distributors'),
    url(r'^v2/repositories/(?P<repo_id>[^/]+)/distributors/(?P<distributor_id>[^/]+)/$',
        RepoDistributorResourceView.as_view(), name='repo_distributor_resource'),
    url(r'^v2/repositories/(?P<repo_id>[^/]+)/distributors/(?P<distributor_id>[^/]+)/schedules/publish/$',
        RepoPublishSchedulesView.as_view(), name='repo_publish_schedules'),
    url(r'^v2/repositories/(?P<repo_id>[^/]+)/distributors/(?P<distributor_id>[^/]+)/schedules/publish/(?P<schedule_id>[^/]+)/$',
        RepoPublishScheduleResourceView.as_view(), name='repo_publish_schedule_resource'),
    url(r'^v2/repositories/(?P<repo_id>[^/]+)/history/sync/$', RepoSyncHistory.as_view(),
        name='repo_sync_history'),
    url(r'^v2/repositories/(?P<repo_id>[^/]+)/history/publish/(?P<distributor_id>[^/]+)/$',
        RepoPublishHistory.as_view(), name='repo_publish_history'),
    url(r'^v2/repositories/(?P<repo_id>[^/]+)/actions/sync/$', RepoSync.as_view(),
        name='repo_sync'),
    url(r'^v2/repositories/(?P<repo_id>[^/]+)/actions/publish/$', RepoPublish.as_view(),
        name='repo_publish'),
    url(r'^v2/repositories/(?P<dest_repo_id>[^/]+)/actions/associate/$', RepoAssociate.as_view(),
        name='repo_associate'),
    url(r'^v2/repositories/(?P<repo_id>[^/]+)/actions/unassociate/$', RepoUnassociate.as_view(),
        name='repo_unassociate'),
    url(r'^v2/repositories/(?P<repo_id>[^/]+)/actions/import_upload/$', RepoImportUpload.as_view(),
        name='repo_import_upload'),
    url(r'^v2/roles/$', RolesView.as_view(), name='roles'),
    url(r'^v2/roles/(?P<role_id>[^/]+)/$', RoleResourceView.as_view(), name='role_resource'),
    url(r'^v2/roles/(?P<role_id>[^/]+)/users/$', RoleUsersView.as_view(), name='role_users'),
    url(r'^v2/roles/(?P<role_id>[^/]+)/users/(?P<login>[^/]+)/$', RoleUserView.as_view(), name='role_user'),
    url(r'^v2/status/$', StatusView.as_view(), name='status'),
    url(r'^v2/tasks/$', tasks.TaskCollectionView.as_view(), name='task_collection'),
    url(r'^v2/tasks/search/$', tasks.TaskSearchView.as_view(), name='task_search'),
    url(r'^v2/tasks/(?P<task_id>[^/]+)/$', tasks.TaskResourceView.as_view(), name='task_resource'),
    url(r'^v2/task_groups/(?P<group_id>[^/]+)/state_summary/$',
        task_groups.TaskGroupSummaryView.as_view(), name='task_group_summary'),
    url(r'^v2/users/$', users.UsersView.as_view(), name='users'),
    url(r'^v2/users/search/$', users.UserSearchView.as_view(),
        name='user_search'),
    url(r'^v2/users/(?P<login>[^/]+)/$', users.UserResourceView.as_view(), name='user_resource')
)
