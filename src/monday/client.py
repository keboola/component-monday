import logging
import json
import requests

# DIR_PATH = os.path.join(os.path.basename(os.getcwd()),'monday')

MONDAY_URL = 'https://api.monday.com/v2'

MONDAY_ENDPOINT_CONFIGS = {
    'activity_logs': {
        'endpoint': 'activity_logs',
        'dataType': 'data.boards'
    },
    'boards': {
        'endpoint': 'boards',
        'dataType': 'data.boards',
        'pagination': 'page'
    },
    'items': {
        'endpoint': 'items',
        'dataType': 'data.items'
    },
    'tags': {
        'endpoint': 'tags',
        'dataType': 'data.tags'
    },
    'teams': {
        'endpoint': 'teams',
        'dataType': 'data.teams'
    },
    'updates': {
        'endpoint': 'updates',
        'dataType': 'data.updates'
    },
    'users': {
        'endpoint': 'users',
        'dataType': 'data.users'
    }
}


class Monday:
    def __init__(self, api_token):
        self.API_TOKEN = api_token

    @staticmethod
    def post_request(url, api_token, body):

        headers = {
            'Authorization': api_token,
            'Content-Type': 'application/json'
        }

        r = requests.post(
            url=url,
            headers=headers,
            data=json.dumps(body)
        )

        if r.status_code != 200:
            raise Exception(f"Request failed with status code {r.status_code}. Response content: {r.text}")

        return r.json()

    @staticmethod
    def fetch_query(endpoint):

        # fetching graphql query
        # graphql_filename = f'monday/graphql_queries/{endpoint}.gql'
        graphql_filename = f'/code/src/monday/graphql_queries/{endpoint}.gql'
        with open(graphql_filename, 'r') as f:
            graphql_query = {
                'query': f.read()
            }
        f.close()

        return graphql_query

    @staticmethod
    def _construct_query(request_body, additional_parameters):

        temp_body = request_body.copy()
        for i in additional_parameters:
            wildcard = '{{' + i + '}}'
            temp_body['query'] = temp_body['query'].replace(
                wildcard, str(additional_parameters[i]))

        return temp_body

    def fetch(self, endpoint, mapping_parser, additional_parameters=None):
        iterator = True

        # request parameters
        body = self.fetch_query(endpoint)

        # query parameters
        pagination_parameters = {
            'page': 1,
            'limit': 200
        }

        if additional_parameters:
            for i in additional_parameters:
                pagination_parameters[i] = additional_parameters[i]

        while iterator:

            # check if query has pagination
            if '{{page}}' not in body:
                logging.debug(f'Pagination NOT detected for [{endpoint}], will only fetch first page.')
                iterator = False

            logging.info(f'Processing [{endpoint}] - Page {pagination_parameters["page"]}')

            request_body = self._construct_query(body, pagination_parameters)

            logging.debug(f"request_body: {request_body}")

            data_in = self.post_request(url=MONDAY_URL, api_token=self.API_TOKEN, body=request_body)

            logging.debug(f"Response: {data_in}")

            endpoint_data_in = mapping_parser.fetch_value(data_in, MONDAY_ENDPOINT_CONFIGS[endpoint]['dataType'])

            # Pagination settings
            if endpoint == 'activity_logs':
                endpoint_data_in_len = 0
                for i in endpoint_data_in:
                    endpoint_data_in_len += len(i['activity_logs'])
            else:
                endpoint_data_in_len = len(endpoint_data_in)

            if endpoint_data_in_len > 0:
                mapping_parser.parse(endpoint_data=endpoint_data_in)

                # adjust pagination parameters
                pagination_parameters['page'] += 1
            else:
                iterator = False
