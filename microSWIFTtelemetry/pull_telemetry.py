"""
Core module for accessing microSWIFT data from the UW-APL SWIFT server.
#TODO:
- needs docstr updates and flake linting
"""

__all__ = [
    "create_request",
    "pull_telemetry_as_var",
    "pull_telemetry_as_zip",
    "pull_telemetry_as_json",
    "pull_telemetry_as_kml",
]

import json
import os

from datetime import datetime, timezone
from typing import Union, Literal, Optional
from urllib.request import urlopen
from urllib.parse import urlencode, quote_plus
from zipfile import ZipFile

from io import BytesIO
from pandas import DataFrame
from xarray import Dataset
from microSWIFTtelemetry.sbd.message_compiler import compile_sbd

# Type aliases
CompiledData = Union[dict, DataFrame, Dataset]
CompiledErrors = Union[dict, DataFrame, Dataset]


def create_request(
    buoy_id: str,
    start_date: datetime,
    end_date: datetime,
    format_out: Literal['zip', 'json', 'kml'],
) -> str:
    """
    TODO: update

    Create a URL-encoded request.

    Arguments:
        - buoy_id (str), microSWIFT ID (e.g. '043')
        - start_date (datetime), query start date in UTC
        - end_date (datetime), query end date in UTC
        - format_out (str), format to query the SWIFT server for:
            * 'zip', return a `.zip` file of SBD messages
            * 'json', JSON-formatted text
            * 'kml', kml of drift tracks

    Returns:
        - (dict), URL-enoded (utf8) request to be sent to the server
    """

    # Convert dates to strings:
    start_date_str = start_date.strftime('%Y-%m-%dT%H:%M:%S')
    end_date_str = end_date.strftime('%Y-%m-%dT%H:%M:%S')

    # Pack into a payload dictionary:
    payload = {
        'buoy_name': f'microSWIFT {buoy_id}'.encode('utf8'),
        'start': start_date_str.encode('utf8'),
        'end': end_date_str.encode('utf8'),
        'format': format_out.encode('utf8')
    }

    return urlencode(payload, quote_via=quote_plus)


def pull_telemetry_as_var(
    buoy_id: str,
    start_date: datetime,  # TODO: include pd.Datetime
    end_date: datetime = datetime.now(timezone.utc),
    var_type: Literal['dict', 'pandas', 'xarray'] = 'dict',
    return_errors: bool = False,
) -> Union[CompiledData, tuple[CompiledData, CompiledErrors]]:
    """
    TODO: update
    Query the SWIFT server for microSWIFT data over a specified date
    range and return an object in memory. Note the `.zip` file of short
    burst data (SBD) messages is handled in memory and not saved to the
    local machine. Use pull_telemetry_as_zip for this purpose.

    Arguments:
        - buoy_id (str), three-digit microSWIFT ID (e.g. '043')
        - start_date (datetime), query start date in UTC
        - end_date (datetime, optional), query end date in UTC; defaults
                to datetime.now(timezone.utc).
        - var_type (str, optional), variable type to return;
                defaults to 'dict'
            Possible values include:
            * 'dict', returns a dictionary of lists
            * 'pandas', returns a pandas DataFrame object
            * 'xarray', returns an xarray DataArray object

    Returns:
        - (List[dict]), if var_type == 'dict'
        - (DataFrame), if var_type == 'pandas'
        - (DataArray), if var_type == 'xarray'

    Example:

    Return SWIFT as a pandas dataframe; by leaving the end_date empty,
    the function will default to the present time (in UTC):

        >>> from datetime import datetime
        >>> import pandas
        >>> SWIFT_df = pull_telemetry_as_var('019', datetime(2022,9,26),
                                             var_type = 'pandas')
    """
    FORMAT_OUT = 'zip'
    BASE_URL = 'http://swiftserver.apl.washington.edu/services/buoy?action=get_data&'

    # TODO: Loop for multiple Ids should happen here
    # Query the SWIFT server
    request = create_request(buoy_id, start_date, end_date, FORMAT_OUT)
    response = urlopen(BASE_URL + request)

    # Read the response into memory as a virtual zip file:
    zipped_file = ZipFile(BytesIO(response.read()))  # virtual zip file
    response.close()
    #TODO: can the zip files be aggregated before compiling?

    # Compile SBD messages into specified variable
    data, errors = compile_sbd(zipped_file, var_type, from_memory=True)

    if return_errors:
        return data, errors
    else:
        return data


def pull_telemetry_as_zip(
    buoy_id: str,
    start_date: datetime,
    end_date: datetime = datetime.now(timezone.utc),
    local_path: Optional[str] = None,
) -> None:
    """
    TODO: update

    Query the SWIFT server for microSWIFT data over a specified date
    range and download a `.zip` file of individual short burst data
    (SBD) messages.

    Arguments:
        - buoy_id (str), microSWIFT ID (e.g. '043')
        - start_date (datetime), query start date in UTC
        - end_date (datetime, optional), query end date in UTC; defaults
                to datetime.now(timezone.utc).
        - local_path (str, optional), path to local file destination
                including folder and filename; defaults to the current
                directory as './microSWIFT{buoy_id}.zip'

    Returns:
        - (BinaryIO), compressed `.zip` file at local_path

    Example:

    Download zipped file of SBD messages; by leaving the end_date empty,
    the function will default to the present time (in UTC):

        >>> from datetime import datetime
        >>> pull_telemetry_as_zip(buoy_id = '019',
                                  start_date = datetime(2022,9,26))
    """
    FORMAT_OUT = 'zip'
    BASE_URL = 'http://swiftserver.apl.washington.edu/services/buoy?action=get_data&'

    # Query the SWIFT server
    request = create_request(buoy_id, start_date, end_date, FORMAT_OUT)
    response = urlopen(BASE_URL + request)

    # Write the response to a local .zip file:
    zipped_file = response.read()
    response.close()

    if local_path is None:
        local_path = os.path.join(os.getcwd(),
                                  f'microSWIFT{buoy_id}.zip')

    with open(local_path, 'wb') as local:
        local.write(zipped_file)
        local.close()

    return None


def pull_telemetry_as_json(
    buoy_id: str,
    start_date: datetime,
    end_date: datetime = datetime.now(timezone.utc),
) -> dict:
    """
    Query the SWIFT server for microSWIFT data over a specified date
    range and download a `.zip` file of individual short burst data
    (SBD) messages.

    Arguments:
        - buoy_id (str), microSWIFT ID (e.g. '043')
        - start_date (datetime), query start date in UTCs
        - end_date (datetime, optional), query end date in UTC; defaults
                to datetime.now(timezone.utc).

    Returns:
        - (dict), JSON-formatted Python dictionary

    Example:

    Query the SWIFT server and return a variable containing JSON-
    formatted text. Save to a .json file.

        >>> from datetime import datetime
        >>> import json
        >>> SWIFT_json = pull_telemetry_as_json(
                            buoy_id = '019',
                            start_date = datetime(2022,9,26),
                            end_date = datetime(2022,9,30)
                        )
        >>> with open('SWIFT.json', 'w') as f:
        >>>     json.dump(SWIFT_json, f)
    """
    FORMAT_OUT = 'json'
    BASE_URL = 'http://swiftserver.apl.washington.edu/kml?action=kml&'

    # Query the SWIFT server
    request = create_request(buoy_id, start_date, end_date, FORMAT_OUT)
    response = urlopen(BASE_URL + request)

    # Return as json
    json_data = response.read()
    response.close()

    return json.loads(json_data)


def pull_telemetry_as_kml(
    buoy_id: str,
    start_date: datetime,
    end_date: datetime = datetime.now(timezone.utc),
    local_path: Optional[str] = None,
) -> None:
    """
    Query the SWIFT server for microSWIFT data over a specified date
    range and download a `.kml` file containing the buoy's coordinates.

    Arguments:
        - buoy_id (str), microSWIFT ID (e.g. '043')
        - start_date (datetime), query start date in UTC
        - end_date (datetime, optional), query end date in UTC; defaults
                to datetime.now(timezone.utc).
        - local_path (str, optional), path to local file destination
                including folder and filename; defaults to the current
                directory as ./microSWIFT{buoy_id}_{'%Y-%m-%dT%H%M%S'}
                _to_{'%Y-%m-%dT%H%M%S'}.kml

    Returns:
        - (TextIO), .kml file at local_path

    Example:

    Download a KML file of buoy drift tracks; by leaving the end_date
    empty, the function will default to the present time (in UTC):

        >>> from datetime import datetime
        >>> pull_telemetry_as_kml(buoy_id = '019',
                                  start_date = datetime(2022,9,26))
    """
    FORMAT_OUT = 'kml'
    BASE_URL = 'http://swiftserver.apl.washington.edu/kml?action=kml&'

    # Query the SWIFT server
    request = create_request(buoy_id, start_date, end_date, FORMAT_OUT)
    response = urlopen(BASE_URL + request)

    # Write the response to a local .kml geographic file:
    kml_file = response.read()
    response.close()
    if local_path is None:
        start_date_str = start_date.strftime('%Y-%m-%dT%H%M%S')
        end_date_str = end_date.strftime('%Y-%m-%dT%H%M%S')
        local_path = os.path.join(
            os.getcwd(),
            f'microSWIFT{buoy_id}_{start_date_str}_to_{end_date_str}.kml'
        )
    with open(local_path, 'wb') as local:
        local.write(kml_file)

    return None
