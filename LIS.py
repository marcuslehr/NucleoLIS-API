import requests
import re
import xml.etree.ElementTree as ET
import pandas as pd


# region External module functions
def login(url, username, pass_file='api_pass.txt'):
    # Save url to module env
    url = set_url(url)

    # Retrieve password
    try:
        with open(pass_file, 'r') as f:
            password = f.read()
    except FileNotFoundError:
        password = input('Enter your password: ')

    # Use global variable to save response to module env for debugging
    global response

    # Call API
    response = requests.post(url + "authenticate/logon",
                             headers={'Content-Type': 'application/x-www-form-urlencoded'},
                             data='username='+username+'&password='+password)

    # Check response
    root = ET.fromstring(response.text)
    if root.text == 'Success':
        print('Login success')

        # Save user ID to module env
        global user_id
        user_id = re.findall("(?<=username=)\\d*?(?=&|$)", str(response.cookies))[0]

        # Save cookie to module env
        get_cookie(response)
    else:
        print('Login failed')


def get_all(method=['cases', 'patients', 'specimens', 'tests', 'physicians'],
            filter_expression="", activesOnly='false',
            last_name='*', first_name='*',
            case_number='*', order_date_from='*', order_date_to='*',
            submitting_physicians='*', submitting_groups='*',
            received_date_from='*', received_date_to='*',
            specimen_status_steps='*', specimen_sources='*',
            order_status_steps='', order_codes=''):

    # Set uri for desired method
    methods = {'heartbeat': 'N/GetHeartbeat',
               'patients': 'N/GetPatients',
               'cases': 'N/GetCases',
               'specimens': 'N/GetSpecimens',
               'tests': 'N/GetTestOrders',
               'physicians': 'N/GetPhysicians'}
    if type(method) is list:
        method = method[0]
    uri = methods.get(method)
    if type(uri) is None:
        print('Invalid method specified.')
        return

    # Set get parameters
    params = dict(filter_expression=filter_expression, activesOnly=activesOnly,
                  last_name=last_name, first_name=first_name,
                  case_number=case_number, order_date_from=order_date_from, order_date_to=order_date_to,
                  submitting_physicians=submitting_physicians, submitting_groups=submitting_groups,
                  received_date_from=received_date_from, received_date_to=received_date_to,
                  specimen_status_steps=specimen_status_steps, specimen_sources=specimen_sources,
                  order_status_steps=order_status_steps, order_codes=order_codes)

    # Call API
    response = api_call(uri, **params)

    # Stop on error
    if error:
        return

    # Convert response to df
    return xml_to_df(response.text)


def get_single(method=['case', 'patient', 'specimen', 'test', 'physician'],
               patient_id=None, case_number=None, specimen_id=None,
               test_order_id=None, physician_code=None):

    # Set uri for desired method
    methods = {'patient': 'N/GetPatient',
               'case': 'N/GetCase',
               'specimen': 'N/GetSpecimen',
               'test': 'N/GetTestOrder',
               'physician': 'N/GetPhysician'}
    if type(method) is list:
        method = method[0]
    uri = methods.get(method)
    if type(uri) is None:
        print('Invalid method specified.')
        return

    # Check that appropriate ID argument is supplied for method call
    IDs = {'patient': patient_id,
           'case': case_number,
           'specimen': specimen_id,
           'test': test_order_id,
           'physician': physician_code}
    ID = IDs.get(method)
    if type(ID) is None:
        print('You must supply the appropriate ID for the selected method')
        return

    # Set get parameters
    params = dict(patient_id=patient_id, case_number=case_number, specimen_id=specimen_id,
                  test_order_id=test_order_id, physician_code=physician_code)

    # Call API
    response = api_call(uri, **params)

    # Stop on error
    if error:
        return

    # Convert response to df
    return xml_to_df(response.text)

def set_status(object_ids, status_set='', status_advance='false'):

    # Paste IDs
    if isinstance(object_ids, (list, set, pd.core.series.Series)):
        object_ids = '|'.join(object_ids)
    else:
        object_ids = int(object_ids)

    # Set get parameters
    params = dict(object_ids=object_ids, status_set=status_set,
                  status_advance=status_advance)

    # Call API
    response = api_call('N/SetStatusSteps', **params)

    # Stop on error
    if error:
        return

    # Convert response to df
    df = xml_to_df(response.text)

    if df is None:
        print('No updates performed. Invalid object ID')

    return df

def api_call(endpoint='GetHeartbeat', **params):

    # Make sure user has logged in
    if 'user_id' not in globals():
        global error
        error = True
        return print('You are not logged in.')

    # Coerce endpoint formatting
    endpoint = re.sub('^/', '', endpoint)
    if re.search('^api/', endpoint) is not None:
        endpoint = re.sub('^api/', '', endpoint)
    if re.search('^N/', endpoint) is None:
        endpoint = re.sub('^', 'N/', endpoint)

    # Add or coerce static params
    params['user_id'] = user_id
    params['return_format'] = '0'

    # Use global variable to save response to module env for debugging
    global response

    # Call API
    response = requests.get(url + endpoint, headers={'Cookie': cookie}, params=params)

    # Parse errors
    parse_errors(response)

    # Return refreshed cookie
    get_cookie(response)

    return response

# endregion


# region Internal module functions.
# These are still user accessible but keeping as single file for simplicity
def get_cookie(response):
    global cookie
    match = re.search("(?<=Cookie ).*?(?=\\s)", str(response.cookies))
    if match is not None:
        cookie = match.group()

def set_url(link):
    if re.search('/api/$', link) is None:
        if re.search('/api$',link) is not None:
            link = re.sub('/api$','/api/',link)
        elif re.search('/$',link) is not None:
            link = re.sub('/$','/api/',link)
        else:
            link = re.sub('$','/api/',link)
    global url
    url = link
    return link

def parse_errors(response):
    error_count = 0

    if response.status_code != 200:
        print('HTTP error: ' + str(response.status_code) + ': ' + response.reason)
        error_count += 1

    if response.status_code == 401:
        print('You are not logged in.')
        error_count += 1

    if re.search("^<Error", response.text) is not None:
        error_message = re.findall("(?<=<Message>).*(?=</Message>)", response.text)
        message_detail = re.search("(?<=<MessageDetail>).*(?=</MessageDetail>)", response.text)
        print(error_message[0])
        print(message_detail.group())
        error_count += 1

    global error
    error = False
    if error_count > 0:
        error = True

def xml_to_df(xml_string):
    root = ET.fromstring(xml_string)

    if root.text == 'No data':
        print('No data returned')
        return

    rows = list()
    for row in root:
        row_dict = dict()
        for column in row:
            row_dict[column.tag] = column.text
        rows.append(row_dict)
    df = pd.DataFrame(rows)

    if df.empty:
        print('No data returned')
    return df

# endregion
