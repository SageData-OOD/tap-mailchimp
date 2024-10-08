"""Stream type classes for tap-mailchimp."""

from __future__ import annotations
import json
from pathlib import Path
from dateutil.parser import isoparse

from singer_sdk import typing as th  # JSON Schema typing helpers

from singer_sdk.pagination import BaseOffsetPaginator

from tap_mailchimp.client import MailchimpStream, MailchimpPaginator

# TODO: Delete this is if not using json files for schema definition
SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")
# TODO: - Override `UsersStream` and `GroupsStream` with your own stream definition.
#       - Copy-paste as many times as needed to create multiple stream types.

class CampaignsStream(MailchimpStream):
    """Define custom stream."""

    name = "campaigns"
    path = "/campaigns"
    response_key = "campaigns"
    primary_keys = ["id"]
    replication_method = 'FULL_TABLE'

    def get_child_context(self, record: dict, context: dict | None) -> dict | None:
        return {
            'campaign_id': record['id']
        }


class ReportsEmailActivity(MailchimpStream):

    name = 'reports_email_activity'
    path = '/reports/{campaign_id}/email-activity'
    parent_stream_type = CampaignsStream
    response_key = 'emails'
    primary_keys = []
    ignore_parent_replication_key = True
    replication_key = 'timestamp'

    def get_records(self, context: dict | None) -> Iterable[dict[str, Any]]:
        for record in self.request_records(context):
            transformed_record = self.post_process(record, context)
            activities = transformed_record.pop('activity')
            for activity in activities:
                yield {**transformed_record, **activity}

    def get_url_params(self, context: dict | None, next_page_token: Any | None) -> dict[str, Any]:
        # get any changes in parent method
        params = super().get_url_params(context, next_page_token)
        # then specialise for this endpoint only with the 'since last changed' param
        params['since'] = self.get_starting_timestamp(context)
        return params
    
class ReportsSentTo(MailchimpStream):

    name = 'reports_sent_to'
    path = '/reports/{campaign_id}/sent-to'
    parent_stream_type = CampaignsStream
    response_key = 'sent_to'
    replication_method = 'FULL_TABLE'
    primary_keys = ['campaign_id', 'email_id']
    ignore_parent_replication_key = True
    exclude_fields = [
        '_links',
    ]


class ListsStream(MailchimpStream):
    """Define custom stream."""

    name = "lists"
    path = "/lists"
    response_key = "lists"
    primary_keys = ["id"]
    replication_method = 'FULL_TABLE'

    def get_child_context(self, record: dict, context: dict | None) -> dict | None:
        return {
            'list_id': record['id']
        }


class ListsMembersStream(MailchimpStream):
    """Define custom stream."""

    name = 'lists_members'
    parent_stream_type = ListsStream
    path = '/lists/{list_id}/members'
    response_key = 'members'
    primary_keys = ['id', 'list_id']
    ignore_parent_replication_key = True
    exclude_fields = [
        '_links',
    ]
    replication_key = 'last_changed'

    def get_url_params(self, context: dict | None, next_page_token: Any | None) -> dict[str, Any]:
        # get any changes in parent method
        params = super().get_url_params(context, next_page_token)
        # then specialise for this endpoint only with the 'since last changed' param
        params['since_last_changed'] = self.get_starting_timestamp(context)
        return params

    def post_process(self, row, context=None)-> dict | None:
        # Assuming `record['custom_data']` is a dictionary
        if "merge_fields" in row:
            # Serialize the custom_data field to a JSON string
            row['merge_fields'] = json.dumps(row['merge_fields'])

        timestamp_opt = row.get("timestamp_opt")

        if isinstance(timestamp_opt, str) and timestamp_opt == "":
            row["timestamp_opt"] = None

        timestamp_signup = row.get("timestamp_signup")

        if isinstance(timestamp_signup, str) and timestamp_signup == "":
            row["timestamp_signup"] = None

        return row

class ReportsUnsubscribes(MailchimpStream):

    name = 'reports_unsubscribes'
    path = '/reports/{campaign_id}/unsubscribed'
    parent_stream_type = CampaignsStream
    response_key = 'unsubscribes'
    primary_keys = [
        'campaign_id',
        'email_id',
    ]
    ignore_parent_replication_key = True
    replication_key = 'timestamp'
    is_sorted = False

    def get_records(self, context: dict | None) -> Iterable[dict[str, Any]]:
        for record in self.request_records(context):
            transformed_record = self.post_process(record, context)
            if isoparse(record['timestamp']) >= self.get_starting_timestamp(context):
                yield record

    def get_url_params(self, context: dict | None, next_page_token: Any | None) -> dict[str, Any]:
        # get any changes in parent method
        params = super().get_url_params(context, next_page_token)
        # then specialise for this endpoint only with the 'since last changed' param
        params['since'] = self.get_starting_timestamp(context)
        return params
