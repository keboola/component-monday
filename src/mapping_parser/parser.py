import os
import json
import pandas as pd


# with open('/code/src/mapping_parser/mapping.json') as f:
with open('mapping_parser/mapping.json') as f:
    MAPPING = json.load(f)


class MappingParser():
    def __init__(self, destination, endpoint, incremental=False, mapping=None):

        self.destination = destination
        self.endpoint = endpoint
        self.mapping = mapping if mapping else MAPPING[endpoint]
        self.incremental = incremental

    def parse(self, endpoint_data, parent_key=None):
        output = []
        primary_key = []

        # Countermeasures for response coming in as DICT
        if type(endpoint_data) == dict:
            endpoint_data = [endpoint_data]

        for row in endpoint_data:
            row_json = {}

            for m in self.mapping:
                col_type = self.mapping[m].get('type') if type(
                    self.mapping[m]) != str else 'string'

                if col_type == 'string':
                    key = self.mapping[m]
                    value = self._fetch_value(row=row, key=m)
                    row_json[key] = value

                elif col_type == 'column' or not col_type:
                    key = self.mapping[m]['mapping']['destination']
                    # value = row[m]
                    value = self._fetch_value(row=row, key=m)
                    row_json[key] = value

                    # Primary key for incremental load
                    if "primaryKey" in self.mapping[m]['mapping'] and key not in primary_key:
                        primary_key.append(key)

                elif col_type == 'user':
                    key = self.mapping[m]['mapping']['destination']
                    value = parent_key
                    row_json[key] = value

                    # Primary key for incremental load
                    primary_key.append(
                        key) if key not in primary_key else ''

                elif col_type == 'table':
                    endpoint = self.mapping[m]['destination']
                    mapping = self.mapping[m]['tableMapping']
                    parent_key = row['id']
                    data = self._fetch_value(row=row, key=m)
                    # Failsafe for entities which are empty are do not have values
                    data = [] if not data else data

                    tableParser = MappingParser(
                        destination=self.destination,
                        endpoint=endpoint,
                        mapping=mapping,
                        incremental=self.incremental
                    )
                    tableParser.parse(endpoint_data=data,
                                      parent_key=parent_key)

            output.append(row_json)

        # Output the chunk
        if output:
            self._output(df_json=output,
                         filename=self.endpoint,
                         primary_key=primary_key)

    @staticmethod
    def _fetch_value(row, key):
        '''
        Fetching value from a nested object
        '''
        key_list = key.split('.')
        value = row

        try:
            for k in key_list:
                value = value[k]

        except Exception:
            value = ''

        return value

    def _output(self, df_json, filename, primary_key):
        output_filename = f'{self.destination}/{filename}.csv'
        if df_json:
            data_output = pd.DataFrame(df_json, dtype=str)
            if not os.path.isfile(output_filename):
                with open(output_filename, 'w') as b:
                    data_output.to_csv(b, index=False)
                b.close()

                # output manifest
                self._produce_manifest(
                    filename=self.endpoint, incremental=self.incremental, primary_key=primary_key)

            else:
                with open(output_filename, 'a') as b:
                    data_output.to_csv(b, index=False, header=False)
                b.close()

    def _produce_manifest(self, filename, incremental, primary_key):
        manifest_filename = f'{self.destination}/{filename}.csv.manifest'
        manifest = {
            'incremental': incremental,
            'primary_key': primary_key,
        }

        with open(manifest_filename, 'w') as file_out:
            json.dump(manifest, file_out)
