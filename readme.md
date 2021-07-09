This is a simple module to interface with the [NucleoLIS](https://psychesystems.com/enterprise-laboratory-information-software/nucleolis-molecular-lab-testing-software/) API.

The module provides 3 functions: login(), get_all(), and get_single(). The functions have the following methods:
get_all() | get_single()
:------: | :------:
cases | case
patients | patient
specimens | specimen
tests | test
physicians | physician
heartbeat |

The get_all() function retrieves summary data of all the records within any of the various data types while the get_single function can be used to retrieve detailed information about a particular record.

More details can be found in the 'Backbone NucleoLIS' documentation pdf in this repository.

Example usage:
'''
import LIS

# First you must login to the API. The password should be stored in a plain text file.
LIS.login(url="https://your.server.com/api/",
          username='user', pass_file='api_pass.txt')

# The login will provide a cookie which is stored within the module environment. The cookie is only valid for 15 mins, however a new cookie provided with each call and is updated automatically within the module. This creates a 15 min timeout period that will require you to login again if you haven't made any API calls for 15 mins


# Fetch some data. A pandas dataframe will be returned 
cases = LIS.get_all('cases')

# You can also apply filters to the call
filtered_cases = LIS.get_all('cases', filter_expression="Patient_Name='Last, First'")

# When retrieving a case, a list will be returned containing a dataframe and a series of metadata. Other retrieval methods will simply return a dataframe
single_case = LIS.get_single('case', case_number='CLIN2020-000002')
'''
