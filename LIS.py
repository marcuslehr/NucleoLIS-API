import requests
import re
import xml.etree.ElementTree as ET
import pandas as pd

class Client:
    def __init__(self, url=None):
        self.url = None
        self.cookie = None
        self.user_id = None
        self.response = None
        if url:
            self.set_url(url)

    def login(self, username, pass_file='api_pass.txt', url=None):

        # Validate/fetch parameters
        if url is not None:
            self.set_url(url)
        elif self.url is None:
            raise ValueError("API URL must be set before logging in.")

        try:
            with open(pass_file, 'r') as f:
                password = f.read()
        except FileNotFoundError:
            password = input('Enter your password: ')

        # Call API to log in
        self.response = requests.post(
            self.url + "authenticate/logon",
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data=f'username={username}&password={password}'
        )

        # Check response and extract user ID and session cookie
        root = ET.fromstring(self.response.text)
        if root.text == 'Success':
            print('Login success')
            self.cookie = self.response.cookies.get('session')
            self.user_id = re.findall("(?<=username=)\\d*?(?=&|$)", str(self.cookie))[0] # It's fine to leave this in the cookie, but it must be extracted and supplied as a param as well
        else:
            raise Exception('Login failed. Please check your username and password.')

    def api_call(self, endpoint='GetHeartbeat', **params):

        # Parse endpoint
        endpoint = re.sub('^/', '', endpoint)
        if re.search('^api/', endpoint) is not None:
            endpoint = re.sub('^api/', '', endpoint)
        if re.search('^N/', endpoint) is None:
            endpoint = re.sub('^', 'N/', endpoint)

        # Add or coerce static params
        if 'params' not in locals():
            params = dict()
        params['user_id'] = self.user_id
        params['return_format'] = '0'

        # Call API
        response = requests.get(
            self.url + endpoint,
            headers={'Cookie': f'session={self.cookie}'},
            params=params
        )

        # Log response for external debugging
        self.response = response

        # Update cookie
        new_cookie = response.cookies.get('session')
        if new_cookie:
            self.cookie = new_cookie

        # Parse errors
        if response.status_code == 401:
            if not self.cookie:
                raise Exception('Session cookie is missing. Please call login() first.')
            else:
                raise Exception('Invalid or expired session. Please login again.')

        if response.status_code == 404:
            raise Exception(f'Endpoint not found: {response.url}'
                            'Note that all parameters must be supplied for any given endpoint.')

        # Capture API specific errors
        if re.search("^<ErrorResponse", response.text) is not None:
            message = re.findall("(?<=<Message>).*(?=</Message>)", response.text)
            message = message[0] if len(message) > 0 else ''

            message_detail = re.search("(?<=<MessageDetail>).*(?=</MessageDetail>)", response.text)
            message_detail = message_detail.group() if message_detail is not None else ''

            raise Exception(
                f'''HTTP code {str(response.status_code)}: {response.reason}
                Server messages-
                {message}
                {message_detail}'''
            )

        return response

    def get_single(self, method=['case', 'patient', 'specimen', 'test', 'physician'],
                   case_number=None, patient_id=None, specimen_id=None,
                   test_order_id=None, physician_code=None):

        # Validate method input
        methods = {
            'patient': 'N/GetPatient',
            'case': 'N/GetCase',
            'specimen': 'N/GetSpecimen',
            'test': 'N/GetTestOrder',
            'physician': 'N/GetPhysician'
        }
        if isinstance(method, list):
            method = method[0]
        endpoint = methods.get(method)
        if endpoint is None:
            raise Exception('Invalid method specified.')

        # Ensure the correct param is provided for method
        id_params = {
            'patient': patient_id,
            'case': case_number,
            'specimen': specimen_id,
            'test': test_order_id,
            'physician': physician_code
        }
        id_value = id_params[method]
        if id_value is None:
            raise Exception(f'You must supply the appropriate ID for the selected method ({method})')

        # Set get parameters. Extra params are ignored.
        params = dict(patient_id=patient_id, case_number=case_number, specimen_id=specimen_id,
                      test_order_id=test_order_id, physician_code=physician_code)

        response = self.api_call(endpoint, **params)

        return self.xml_to_df(response.text)

    def get_all(self, method=['cases', 'patients', 'specimens', 'tests', 'physicians'],
                filter_expression="", activesOnly='false',
                last_name='*', first_name='*',
                case_number='*', order_date_from='*', order_date_to='*',
                submitting_physicians='*', submitting_groups='*',
                received_date_from='*', received_date_to='*',
                specimen_status_steps='*', specimen_sources='*',
                order_status_steps='', order_codes=''
                ):

        # Validate method input
        methods = {
            'cases': 'N/GetCases',
            'patients': 'N/GetPatients',
            'specimens': 'N/GetSpecimens',
            'tests': 'N/GetTestOrders',
            'physicians': 'N/GetPhysicians'
        }
        if isinstance(method, list):
            method = method[0]
        endpoint = methods.get(method)
        if endpoint is None:
            raise Exception('Invalid method specified.')

        # Set get parameters
        params = dict(filter_expression=filter_expression, activesOnly=activesOnly,
                      last_name=last_name, first_name=first_name,
                      case_number=case_number, order_date_from=order_date_from, order_date_to=order_date_to,
                      submitting_physicians=submitting_physicians, submitting_groups=submitting_groups,
                      received_date_from=received_date_from, received_date_to=received_date_to,
                      specimen_status_steps=specimen_status_steps, specimen_sources=specimen_sources,
                      order_status_steps=order_status_steps, order_codes=order_codes)

        # Call API
        response = self.api_call(endpoint, **params)

        # This doesn't seem to be true? Returns empty
        # # API will return None if no results are found
        # if response is None:
        #     return None

        return self.xml_to_df(response.text)

    def set_status(self, object_ids, status_set='', status_advance='false'):

        # Accepts a single id or iterable of ids
        if isinstance(object_ids, (list, set, pd.Series)):
            object_ids = '|'.join(str(i) for i in object_ids)
        else:
            object_ids = int(object_ids) # When called from R, all numbers are fed as floats

        params = dict(object_ids=object_ids,
                      status_set=status_set,
                      status_advance=status_advance)

        response = self.api_call('N/SetStatusSteps', **params)

        update_details = self.xml_to_df(response.text)
        if update_details is None or update_details.empty:
            raise Exception('Invalid object IDs. No updates performed.')

        return update_details

    #region Internal helper functions
    def set_url(self, link):
        # Normalize API URL ending
        if not link.endswith('/api/'):
            if link.endswith('/api'):
                link = link + '/'
            elif link.endswith('/'):
                link = link + 'api/'
            else:
                link = link + '/api/'
        self.url = link
        return self.url

    def xml_to_df(self, xml_string):
        root = ET.fromstring(xml_string)
        if root.text == 'No data':
            print('No data returned')
            return
        rows = []
        for row in root:
            row_dict = {column.tag: column.text for column in row}
            rows.append(row_dict)
        df = pd.DataFrame(rows)
        if df.empty:
            print('No data returned')
            # maybe return None here?
        return df

    #endregion
