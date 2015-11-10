﻿#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
from dateutil import parser
try:
    from xml.etree import cElementTree as ETree
except ImportError:
    from xml.etree import ElementTree as ETree
from .._common_conversion import (
    _decode_base64_to_text,
    _str_or_none,
)
from .._common_serialization import _parse_response_for_dict
from .models import (
    Container,
    Blob,
    BlobList,
    BlobBlock,
    BlobBlockList,
    BlobBlockState,
    BlobProperties,
    PageRange,
)
from ..models import _list

def _convert_xml_to_containers(response):
    '''
    <?xml version="1.0" encoding="utf-8"?>
    <EnumerationResults ServiceEndpoint="https://myaccount.blob.core.windows.net">
      <Prefix>string-value</Prefix>
      <Marker>string-value</Marker>
      <MaxResults>int-value</MaxResults>
      <Containers>
        <Container>
          <Name>container-name</Name>
          <Properties>
            <Last-Modified>date/time-value</Last-Modified>
            <Etag>etag</Etag>
            <LeaseStatus>locked | unlocked</LeaseStatus>
            <LeaseState>available | leased | expired | breaking | broken</LeaseState>
            <LeaseDuration>infinite | fixed</LeaseDuration>      
          </Properties>
          <Metadata>
            <metadata-name>value</metadata-name>
          </Metadata>
        </Container>
      </Containers>
      <NextMarker>marker-value</NextMarker>
    </EnumerationResults>
    '''
    if response is None or response.body is None:
        return response

    containers = _list()
    list_element = ETree.fromstring(response.body)
    
    # Set next marker
    setattr(containers, 'next_marker', list_element.findtext('NextMarker'))

    containers_element = list_element.find('Containers')

    for container_element in containers_element.findall('Container'):
        # Name element
        container = Container()
        container.name = container_element.findtext('Name')

        # Metadata
        metadata_root_element = container_element.find('Metadata')
        if metadata_root_element is not None:
            container.metadata = dict()
            for metadata_element in metadata_root_element:
                container.metadata[metadata_element.tag] = metadata_element.text

        # Properties
        properties_element = container_element.find('Properties')
        container.properties.etag = properties_element.findtext('Etag')
        container.properties.last_modified = parser.parse(properties_element.findtext('Last-Modified'))
        container.properties.lease_status = properties_element.findtext('LeaseStatus')
        container.properties.lease_state = properties_element.findtext('LeaseState')
        container.properties.lease_duration = properties_element.findtext('LeaseDuration')
        
        # Add container to list
        containers.append(container)

    return containers

def _int_or_none(value):
    return value if value is None else int(value)

LIST_BLOBS_ATTRIBUTE_MAP = {
    'Last-Modified': ('last_modified', parser.parse),
    'Etag': ('etag', _str_or_none),
    'Content-Length': ('content_length', _int_or_none),
    'Content-Type': ('content_type', _str_or_none),
    'Content-Encoding': ('content_encoding', _str_or_none),
    'Content-Language': ('content_language', _str_or_none),
    'Content-MD5': ('content_md5', _str_or_none),
    'x-ms-blob-sequence-number': ('sequence_number', _int_or_none),
    'BlobType': ('blob_type', _str_or_none),
    'LeaseStatus': ('lease_status', _str_or_none),
    'LeaseState': ('lease_state', _str_or_none),
    'LeaseDuration': ('lease_duration', _str_or_none),
    'CopyId': ('copy_id', _str_or_none),
    'CopySource': ('copy_source', _str_or_none),
    'CopyStatus': ('copy_status', _str_or_none),
    'CopyProgress': ('copy_progress', _str_or_none),
    'CopyCompletionTime': ('copy_completion_time', _str_or_none),
    'CopyStatusDescription': ('copy_status_description', _str_or_none),
}

def _convert_xml_to_blob_list(response):
    '''
    <?xml version="1.0" encoding="utf-8"?>
    <EnumerationResults ServiceEndpoint="http://myaccount.blob.core.windows.net/" ContainerName="mycontainer">
      <Prefix>string-value</Prefix>
      <Marker>string-value</Marker>
      <MaxResults>int-value</MaxResults>
      <Delimiter>string-value</Delimiter>
      <Blobs>
        <Blob>
          <Name>blob-name</name>
          <Snapshot>date-time-value</Snapshot>
          <Properties>
            <Last-Modified>date-time-value</Last-Modified>
            <Etag>etag</Etag>
            <Content-Length>size-in-bytes</Content-Length>
            <Content-Type>blob-content-type</Content-Type>
            <Content-Encoding />
            <Content-Language />
            <Content-MD5 />
            <Cache-Control />
            <x-ms-blob-sequence-number>sequence-number</x-ms-blob-sequence-number>
            <BlobType>BlockBlob|PageBlob|AppendBlob</BlobType>
            <LeaseStatus>locked|unlocked</LeaseStatus>
            <LeaseState>available | leased | expired | breaking | broken</LeaseState>
            <LeaseDuration>infinite | fixed</LeaseDuration>
            <CopyId>id</CopyId>
            <CopyStatus>pending | success | aborted | failed </CopyStatus>
            <CopySource>source url</CopySource>
            <CopyProgress>bytes copied/bytes total</CopyProgress>
            <CopyCompletionTime>datetime</CopyCompletionTime>
            <CopyStatusDescription>error string</CopyStatusDescription>
          </Properties>
          <Metadata>   
            <Name>value</Name>
          </Metadata>
        </Blob>
        <BlobPrefix>
          <Name>blob-prefix</Name>
        </BlobPrefix>
      </Blobs>
      <NextMarker />
    </EnumerationResults>
    '''
    if response is None or response.body is None:
        return response

    blob_list = BlobList()    
    list_element = ETree.fromstring(response.body)

    setattr(blob_list, 'next_marker', list_element.findtext('NextMarker'))

    blobs_element = list_element.find('Blobs')
    blob_prefix_elements = blobs_element.findall('BlobPrefix')
    if blob_prefix_elements is not None:
        for blob_prefix_element in blob_prefix_elements:
            blob_list.prefixes.append(blob_prefix_element.findtext('Name'))

    for blob_element in blobs_element.findall('Blob'):
        blob = Blob()
        blob.name = blob_element.findtext('Name')
        blob.snapshot = blob_element.findtext('Snapshot')

        # Properties
        properties_element = blob_element.find('Properties')
        if properties_element is not None:
            for property_element in properties_element:
                info = LIST_BLOBS_ATTRIBUTE_MAP.get(property_element.tag)
                if not info:
                    info = property_element.tag, str
                setattr(blob.properties, info[0], info[1](property_element.text))

        # Metadata
        metadata_root_element = blob_element.find('Metadata')
        if metadata_root_element is not None:
            blob.metadata = dict()
            for metadata_element in metadata_root_element:
                blob.metadata[metadata_element.tag] = metadata_element.text
        
        # Add blob to list
        blob_list.blobs.append(blob)

    return blob_list

def _parse_blob(response):
    props, metadata = _parse_blob_properties(response)
    return Blob(response.body, props, metadata)

def _convert_xml_to_block_list(response):
    '''
    <?xml version="1.0" encoding="utf-8"?>
    <BlockList>
      <CommittedBlocks>
         <Block>
            <Name>base64-encoded-block-id</Name>
            <Size>size-in-bytes</Size>
         </Block>
      </CommittedBlocks>
      <UncommittedBlocks>
        <Block>
          <Name>base64-encoded-block-id</Name>
          <Size>size-in-bytes</Size>
        </Block>
      </UncommittedBlocks>
     </BlockList>

    Converts xml response to block list class.
    '''
    if response is None or response.body is None:
        return response

    block_list = BlobBlockList()

    list_element = ETree.fromstring(response.body)

    committed_blocks_element = list_element.find('CommittedBlocks')
    for block_element in committed_blocks_element.findall('Block'):
        block_id = _decode_base64_to_text(block_element.findtext('Name', ''))
        block_size = int(block_element.findtext('Size'))
        block = BlobBlock(id=block_id, state=BlobBlockState.Committed)
        block._set_size(block_size)
        block_list.committed_blocks.append(block)

    uncommitted_blocks_element = list_element.find('UncommittedBlocks')
    for block_element in uncommitted_blocks_element.findall('Block'):
        block_id = _decode_base64_to_text(block_element.findtext('Name', ''))
        block_size = int(block_element.findtext('Size'))
        block = BlobBlock(id=block_id, state=BlobBlockState.Uncommitted)
        block._set_size(block_size)
        block_list.uncommitted_blocks.append(block)

    return block_list

def _convert_xml_to_page_ranges(response):
    '''
    <?xml version="1.0" encoding="utf-8"?>
    <PageList>
       <PageRange>
          <Start>Start Byte</Start>
          <End>End Byte</End>
       </PageRange>
       <PageRange>
          <Start>Start Byte</Start>
          <End>End Byte</End>
       </PageRange>
    </PageList>
    '''
    if response is None or response.body is None:
        return response

    page_list = list()

    list_element = ETree.fromstring(response.body)

    page_range_elements = list_element.findall('PageRange')
    for page_range_element in page_range_elements:
        page_list.append(
            PageRange(
                int(page_range_element.findtext('Start')),
                int(page_range_element.findtext('End'))
            )
        )

    return page_list

GET_BLOB_ATTRIBUTE_MAP = {
    'last-modified': (None, 'last_modified', parser.parse),
    'etag': (None, 'etag', _str_or_none),
    'x-ms-blob-type': (None, 'blob_type', _str_or_none),
    'content-length': (None, 'content_length', _int_or_none),
    'x-ms-blob-sequence-number': (None, 'page_blob_sequence_number', _int_or_none),
    'x-ms-blob-committed-block-count': (None, 'append_blob_committed_block_count', _int_or_none),
    'content-type': ('settings', 'content_type', _str_or_none),
    'cache-control': ('settings', 'cache_control', _str_or_none),
    'content-encoding': ('settings', 'content_encoding', _str_or_none),
    'content-disposition': ('settings', 'content_disposition', _str_or_none),
    'content-language': ('settings', 'content_language', _str_or_none),
    'content-md5': ('settings', 'content_md5', _str_or_none),
    'x-ms-lease-status': ('lease', 'status', _str_or_none),
    'x-ms-lease-state': ('lease', 'state', _str_or_none),
    'x-ms-lease-duration': ('lease', 'duration', _str_or_none),
    'x-ms-copy-id': ('copy', 'id', _str_or_none),
    'x-ms-copy-source': ('copy', 'source', _str_or_none),
    'x-ms-copy-status': ('copy', 'status', _str_or_none),
    'x-ms-copy-progress': ('copy', 'progress', _str_or_none),
    'x-ms-copy-completion-time': ('copy', 'completion_time', _str_or_none),
    'x-ms-copy-status-description': ('copy', 'status_description', _str_or_none),
}

def _parse_blob_properties(response):
    ''' Extracts name-values from response header. Filter out the standard
    http headers.'''

    if response is None and response.headers is not None:
        return None, None

    props = BlobProperties()
    metadata = {}
    for key, value in response.headers:
        info = GET_BLOB_ATTRIBUTE_MAP.get(key)
        if info:
            if info[0] is None:
                setattr(props, info[1], info[2](value))
            else:
                attr = getattr(props, info[0])
                setattr(attr, info[1], info[2](value))
        elif key.startswith('x-ms-meta-'):
            metadata[key] = _str_or_none(value)

    return props, metadata