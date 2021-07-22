This is a simple python module to interface with the [NucleoLIS](https://psychesystems.com/enterprise-laboratory-information-software/nucleolis-molecular-lab-testing-software/) API.

The module provides the following functions: login(), get_all(), get_single(), set_status(), and the generic api_call() function. 

To use the module, first call the login() function. Be sure to include '/api/' at the end of your url, and the password should be stored in a plain text file.
```
import LIS

LIS.login(url="https://your.server.com/api/",
          username='user', pass_file='api_pass.txt')
```
Your login will be valid for 15 minutes. The 15 minute window will be reset with each API call, however if you do not call the API for 15 minutes, you will need to login again.

Once logged in, you can use the other functions to retrieve data. The primary functions for this are get_all() which retrieves summary data of all records and get_single() which retrieves detailed information about a particular record. The functions have the following methods:
get_all() | get_single()
:------: | :------:
cases | case
patients | patient
specimens | specimen
tests | test
physicians | physician
```
# Fetch some data. A pandas dataframe will be returned 
cases = LIS.get_all('cases')

# You can also apply filters to the call
filtered_cases = LIS.get_all('cases', filter_expression="Patient_Name='Last, First'")

# Pull details on a single case. This will also be returned as a dataframe
single_case = LIS.get_single('case', case_number='CLIN2020-000002')
```
For API endpoints not covered by these functions, you can use the generic function api_call(). Note that when using this function all parameters for any given endpoint that are defined in the NucleoLIS documentation must be supplied, otherwise a 404 error will be returned. However, the `user_id` and `return_format` parameters will be supplied by the function automatically.
```
# Perform a generic API call. The raw http response will be returned
response = LIS.api_call('N/GetPhysicianLocations', physician_code='123456')

# To convert this response to a dataframe, we can call one of the 'internal' module functions
df = LIS.xml_to_df(response.text)
```
Additionally, there is the set_status() function which updates `_StatusStep` fields. These fields correspond to the `_ObjectID` fields. For example, if you supply a `Specimen_ObjectID` the `Specimen_StatusStep` field will be updated. These are factor fields that will only accept values which have been predefined in the NucleoLIS software. Multiple IDs should be supplied in a list.
```
# Update status for all cases for the patient selected above
LIS.set_status(object_ids=filtered_cases.Case_ObjectID, status_advance='true')
```
For more information, see the 'Backbone NucleoLIS API' documentation pdf in this repository.