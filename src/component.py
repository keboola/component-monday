'''
kds-team.ex-monday

'''
import sys
import logging
import dateparser

from keboola.component.base import ComponentBase
from keboola.component.exceptions import UserException

from monday.client import Monday
from mapping_parser.parser import MappingParser

# configuration variables
KEY_API_TOKEN = '#api_token'
KEY_ENDPOINT = 'endpoint'
KEY_INCREMENTAL = 'incrementalLoad'

# list of mandatory parameters => if some is missing,
# component will fail with readable message on initialization.
REQUIRED_PARAMETERS = [
    KEY_API_TOKEN,
    KEY_ENDPOINT,
    KEY_INCREMENTAL
]
REQUIRED_IMAGE_PARS = []


class Component(ComponentBase):
    """
        Extends base class for general Python components. Initializes the CommonInterface
        and performs configuration validation.

        For easier debugging the data folder is picked up by default from `../data` path,
        relative to working directory.

        If `debug` parameter is present in the `config.json`, the default logger is set to verbose DEBUG mode.
    """

    def __init__(self):
        super().__init__()

    def validate_input_parameters(self, params, additional_parameters):

        additional_parameters_out = additional_parameters.copy()

        # 1 - check empty configurations
        if params == {}:
            raise UserException('Component is not configured.')

        # 2 - check if api token is enter
        api_token = params.get(KEY_API_TOKEN)
        if not api_token:
            raise UserException('API token is not set.')

        # 3 - check endpoint
        endpoint = params.get(KEY_ENDPOINT)
        if not endpoint:
            raise UserException('Endpoint is not set.')

        # 4 - check additional parmeters for specific endpoints
        if endpoint == 'activity_logs':
            from_date = additional_parameters.get('from_date')
            to_date = additional_parameters.get('to_date')

            from_date_form = dateparser.parse(from_date)
            to_date_form = dateparser.parse(to_date)
            day_diff = (to_date_form-from_date_form).days

            if not from_date or not to_date:
                raise UserException('[From Date] and [To Date] is required.')

            if day_diff < 0:
                raise UserException(
                    '[From Date] cannot exceed [To Date]')

            additional_parameters_out['from_date'] = from_date_form.strftime("%Y-%m-%d")
            additional_parameters_out['to_date'] = to_date_form.strftime("%Y-%m-%d")

        elif endpoint == 'boards':
            state = additional_parameters.get('state')
            board_kind = additional_parameters.get('board_kind')

            if not state or not board_kind:
                raise UserException('[State] and [Board Kind] is required.')

        # 5 - check if API token is valid
        test_client = Monday(api_token=api_token)
        test_query = test_client.fetch_query('me')
        test_url = 'https://api.monday.com/v2'
        test_result = test_client.post_request(
            url=test_url, api_token=params.get(KEY_API_TOKEN), body=test_query)

        if 'errors' in test_result:
            raise Exception(
                'Authentication failed. Please check your API token')

        return additional_parameters_out

    def run(self):
        '''
        Main execution code
        '''

        # User input parameters
        params = self.configuration.parameters

        # component parameters
        api_token = params.get(KEY_API_TOKEN)
        endpoint = params.get(KEY_ENDPOINT)
        incremental = params.get(KEY_INCREMENTAL)
        additional_parameters = {}
        for i in params:
            if i not in REQUIRED_PARAMETERS:
                additional_parameters[i] = params[i]

        # Validate user inputs and adjust parameters if necessary
        additional_parameters = self.validate_input_parameters(params, additional_parameters)

        # Monday request client
        monday_client = Monday(api_token=api_token)

        # Mapping parser client
        endpointParser = MappingParser(
            destination=self.tables_out_path,
            endpoint=endpoint,
            incremental=incremental)

        monday_client.fetch(
            endpoint=endpoint,
            MappingParser=endpointParser,
            additional_parameters=additional_parameters)


"""
        Main entrypoint
"""
if __name__ == "__main__":
    try:
        comp = Component()
        # this triggers the run method by default and is controlled by the configuration.action parameter
        comp.execute_action()
    except UserException as exc:
        logging.exception(exc)
        exit(1)
    except Exception as exc:
        logging.exception(exc)
        exit(2)
