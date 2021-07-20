import requests
import re
import xml.etree.ElementTree as ET
import pandas as pd


# region External module functions
def login(url, username, pass_file='api_pass.txt'):
    # Save url to module env
    set_url(url)

    # Set metadata
    uri = "authenticate/logon"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    # Retrieve password
    try:
        with open(pass_file, 'r') as f:
            password = f.read()
    except FileNotFoundError:
        password = input('Enter your password: ')

    # Call API
    response = requests.post(url + uri, headers=headers,
                             data='username='+username+'&password='+password)

    # Check response
    root = ET.fromstring(response.text)
    if root.text == 'Success':
        print('Login success')
        # Save cookie and ID to module env
        get_cookie(response)
        get_id(response)
    else:
        print('Login failed')


def get_all(method=['cases', 'heartbeat', 'patients', 'specimens', 'tests', 'physicians'],
            filter_expression="", activesOnly='false',
            last_name='*', first_name='*',
            case_number='*', order_date_from='*', order_date_to='*',
            submitting_physicians='*', submitting_groups='*',
            received_date_from='*', received_date_to='*',
            specimen_status_steps='*', specimen_sources='*',
            order_status_steps='', order_codes=''):

    # Make sure user has logged in
    if 'user_id' not in globals():
        return print('You have not logged in.')

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
                  user_id=user_id, return_format='0',
                  last_name=last_name, first_name=first_name,
                  case_number=case_number, order_date_from=order_date_from, order_date_to=order_date_to,
                  submitting_physicians=submitting_physicians, submitting_groups=submitting_groups,
                  received_date_from=received_date_from, received_date_to=received_date_to,
                  specimen_status_steps=specimen_status_steps, specimen_sources=specimen_sources,
                  order_status_steps=order_status_steps, order_codes=order_codes)

    # Call API
    response = requests.get(url + uri, headers={'Cookie': cookie}, params=params)

    # Parse errors
    if response.status_code != 200:
        print('HTTP error: ' + str(response.status_code) + ': ' + response.reason)
        return
    if re.search("^<ErrorResponse>", response.text) is not None:
        error_message = re.findall("(?<=<Message>).*(?=</Message)", response.text)
        print(error_message[0])
        return

    # Return refreshed cookie
    get_cookie(response)

    # Convert response to df
    return xml_to_df(response.text)


def get_single(method=['case', 'patient', 'specimen', 'test', 'physician'],
               patient_id=None, case_number=None, specimen_id=None,
               test_order_id=None, physician_code=None):

    # Make sure user has logged in
    if 'user_id' not in globals():
        return print('You have not logged in.')

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
                  test_order_id=test_order_id, physician_code=physician_code,
                  user_id=user_id, return_format='0')

    # Call API
    response = requests.get(url + uri, headers={'Cookie': cookie}, params=params)

    # Parse errors
    if response.status_code != 200:
        print('HTTP error: ' + str(response.status_code) + ': ' + response.reason)
        return
    if re.search("^<ErrorResponse>", response.text) is not None:
        error_message = re.findall("(?<=<Message>).*(?=</Message)", response.text)
        print(error_message[0])
        return

    # Return refreshed cookie
    get_cookie(response)

    # Convert response to df
    df = xml_to_df(response.text)

    return df

def set_status(object_ids, status_set='', status_advance='false'):

    # Make sure user has logged in
    if 'user_id' not in globals():
        return print('You have not logged in.')

    # Paste IDs
    if isinstance(object_ids, (list, set, pd.core.series.Series)):
        object_ids = '|'.join(object_ids)

    # Set get parameters
    params = dict(object_ids=object_ids, status_set=status_set,
                  status_advance=status_advance,
                  user_id=user_id, return_format='0')

    # Call API
    response = requests.get(url + 'N/SetStatusSteps', headers={'Cookie': cookie}, params=params)

    # Parse errors
    error = parse_errors(response)
    if error: return

    # Return refreshed cookie
    get_cookie(response)

    # Convert response to df
    return xml_to_df(response.text)

# endregion


# region Internal module functions
def get_cookie(response):
    global cookie
    cookie = re.findall("(?<=Cookie ).*?(?=\\s)", str(response.cookies))[0]

def get_id(response):
    global user_id
    user_id = re.findall("(?<=username=)\\d*?(?=&|$)", str(response.cookies))[0]

def set_url(link):
    global url
    url = link

def parse_errors(response):
    # Parse errors
    if response.status_code != 200:
        print('HTTP error: ' + str(response.status_code) + ': ' + response.reason)
        return True
    if re.search("^<ErrorResponse>", response.text) is not None:
        error_message = re.findall("(?<=<Message>).*(?=</Message)", response.text)
        print(error_message[0])
        return True

def xml_to_df(xml_string):
    xml_table = ET.fromstring(xml_string)
    rows = list()
    for patient in xml_table:
        patient_dict = dict()
        for element in patient:
            patient_dict[element.tag] = element.text
        rows.append(patient_dict)
    return pd.DataFrame(rows)

# endregion
