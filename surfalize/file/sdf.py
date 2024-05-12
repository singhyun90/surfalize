import struct
import re
from datetime import datetime
import numpy as np
from .common import read_binary_layout, RawSurface, get_unit_conversion, write_binary_layout
from ..exceptions import CorruptedFileError, UnsupportedFileFormatError

# TODO: Account for non-measured points

# File format specifications taken from ISO 25178-71
MAGIC_ASCII = b'aISO-1.0'
MAGIC_BINARY = b'bISO-1.0'

FIXED_UNIT = 'm'
CONVERSION_FACTOR = get_unit_conversion(FIXED_UNIT, 'um')
ASCII_DATE_FORMAT = "%d%m%Y%H%M"

LAYOUT_HEADER = (
    ("ManufacID", "10s", False),
    ("CreateDate", "12s", False),
    ("ModDate", "12s", False),
    ("NumPoints", "H", False),
    ("NumProfiles", "H", False),
    ("Xscale", "d", False),
    ("Yscale", "d", False),
    ("Zscale", "d", False),
    ("Zresolution", "d", False),
    ("Compression", "B", False),
    ("DataType", "B", False),
    ("CheckType", "B", False),
)

ASCII_HEADER_TYPES = {
    "ManufacID": str,
    "CreateDate": str,
    "ModDate": str,
    "NumPoints": int,
    "NumProfiles": int,
    "Xscale": float,
    "Yscale": float,
    "Zscale": float,
    "Zresolution": float,
    "Compression": int,
    "DataType": int,
    "CheckType": int,
}

DTYPE_MAP = {
    5: "h",  # INT16
    6: "I",  # UINT16
    7: "d",  # DOUBLE
}

def read_ascii_sdf(filehandle, encoding="utf-8"):
    contents = filehandle.read().decode('ascii').lstrip()
    header_section, data_section, trailer_section, end = contents.split('*')
    if end.strip() != '':
        raise ValueError

    header = dict()
    for line in header_section.lstrip().splitlines():
        name, value = line.split('=')
        name, value = name.strip(), value.strip()
        if name not in ASCII_HEADER_TYPES:
            raise CorruptedFileError(f'Unknown header field "{name}" detected.')
        header[name] = ASCII_HEADER_TYPES[name](value)

    if header['DataType'] not in DTYPE_MAP:
        raise CorruptedFileError(f"Unsupported DataType in SDF file: {header['DataType']}")

    data_format = DTYPE_MAP[header['DataType']]

    if 'CreateDate' in header:
        header['CreateDate'] = datetime.strptime(header['CreateDate'], ASCII_DATE_FORMAT)
    if 'ModDate' in header:
        header['ModDate'] = datetime.strptime(header['ModDate'], ASCII_DATE_FORMAT)

    data = np.fromstring(data_section, sep=' ', dtype=data_format).reshape(header['NumProfiles'], header['NumPoints'])
    data *= CONVERSION_FACTOR * header['Zscale']
    step_x = header['Xscale'] * CONVERSION_FACTOR
    step_y = header['Yscale'] * CONVERSION_FACTOR
    metadata = header
    # This regex matches xml tags that may contain whitespace characters
    # E.g. the ISO 25178-71 ASII SDF example contains this exemplary line: < OperatorName > Tom Jones < / OperatorName >
    # If we want to parse this as xml, we need to clean it up first with a regex anyway, so we may as well use it
    # to parse it, even though it is an evil thing to do
    pattern = r'< ?\b(\w+)\b ?>(.*)< ?/ ?\b\1\b ?>'
    metadata.update({k: v.strip() for k, v in re.findall(pattern, data_section)})

    return RawSurface(data, step_x, step_y, metadata=metadata, image_layers=None)

def read_binary_sdf(filehandle, encoding="utf-8"):
    header = read_binary_layout(filehandle, LAYOUT_HEADER, encoding=encoding)
    num_points = header["NumPoints"]
    num_profiles = header["NumProfiles"]
    data_type = header["DataType"]

    if data_type not in DTYPE_MAP:
        raise CorruptedFileError(f"Unsupported DataType in SDF file: {data_type}")

    data_format = DTYPE_MAP[data_type]
    item_size = struct.calcsize(data_format)
    data_size = item_size * num_points * num_profiles
    data_bytes = filehandle.read(data_size)

    if len(data_bytes) != data_size:
        raise CorruptedFileError("Unexpected end of file or corrupt data section.")

    data = np.frombuffer(data_bytes, dtype=np.dtype(data_format))

    data = data * header["Zscale"] * CONVERSION_FACTOR
    data = data.reshape((num_profiles, num_points))
    step_x = header["Xscale"] * CONVERSION_FACTOR
    step_y = header["Yscale"] * CONVERSION_FACTOR
    return RawSurface(data, step_x, step_y, metadata=header)

def read_sdf(file_path, read_image_layers=False, encoding="utf-8"):
    with open(file_path, "rb") as filehandle:
        magic = filehandle.read(8)
        if magic == MAGIC_ASCII:
            return read_ascii_sdf(filehandle, encoding=encoding)
        elif magic == MAGIC_BINARY:
            return read_binary_sdf(filehandle, encoding=encoding)
        else:
            raise CorruptedFileError(f'Invalid file magic "{magic.decode()}" detected.')
def write_sdf(filepath, surface, encoding='utf-8', binary=True):
    now = datetime.now()
    mod_date = now.strftime(ASCII_DATE_FORMAT)
    # if the surface contains a timestamp in the metadata, we use this one, otherwise we set the create date to the same
    # value as the modified date
    if 'timestamp' in surface.metadata:
        create_date = surface.metadata['timestamp'].strftime(ASCII_DATE_FORMAT)
    else:
        create_date = mod_date

    # Here, we divide the data by a power of 10 so that there is only one significant digit before
    # the decimal point. This way, we can make use of the maximum resolution of the ascii encoded
    # decimal places.
    scale_factor = 10 ** (int(np.log10(surface.data.max())))
    data = surface.data.astype('float64') / scale_factor

    conversion_factor = get_unit_conversion('um', FIXED_UNIT)
    header = {
        "ManufacID": 'surfalize'.ljust(10),
        "CreateDate": create_date,
        "ModDate": mod_date,
        "NumPoints": surface.size.x,
        "NumProfiles": surface.size.y,
        "Xscale": surface.step_x * conversion_factor,
        "Yscale": surface.step_y * conversion_factor,
        "Zscale": scale_factor * get_unit_conversion('um', FIXED_UNIT),
        # Zresolution = original base resolution of the measurement instrument
        # The standard says to fill this with a negative number when the value is unknown
        "Zresolution": -1,
        "Compression": 0, # no compression
        "DataType": 7, # data type double should be default
        "CheckType": 0, # should be zero according to standard
    }

    if binary:
        with open(filepath, 'wb') as filehandle:
            filehandle.write(MAGIC_BINARY) # write magic identifier
            write_binary_layout(filehandle, LAYOUT_HEADER, header)
            data.tofile(filehandle)
    else:
        CRLF = '\n'
        with open(filepath, 'w') as filehandle:
            filehandle.write(MAGIC_ASCII.decode() + CRLF)
            for k, v in header.items():
                filehandle.write(f'{k} = {v}{CRLF}')
            filehandle.write('*' + CRLF)
            data.tofile(filehandle, sep=' ', format='%.8f')
            filehandle.write(CRLF + '*' + CRLF)
            filehandle.write('<ExportedBy>Surfalize</ExportedBy>' + CRLF)
            filehandle.write('*' + CRLF)
