import xml.etree.ElementTree as ET
from dwcawriter import Archive, Table
import tempfile
from datetime import datetime
import os
from minio import Minio
from tenacity import retry, stop_after_attempt, wait_fixed

def make_eml(title, description):
    tree = ET.parse('templates/eml.xml')
    root = tree.getroot()
    placeholder_user = {'givenName': 'Test', 'surName': 'User', 'userId': '0000-0002-1825-0097'}
    values = {
        'title': title,
        'creator': placeholder_user, 
        'metadataProvider': placeholder_user,
        'abstract' : { 'para': description }
    }

    def fill_node(node, values):
        for key, value in values.items():
            child = node.find(f'.//{key}')
            if child is not None:
                if isinstance(value, dict):
                    fill_node(child, value)
                else:
                    child.text = value
    fill_node(root, values)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True).decode('utf-8')

@retry(stop=stop_after_attempt(10), wait=wait_fixed(2))
def upload_file(client, bucket_name, object_name, local_path):
    client.fput_object(bucket_name, object_name, local_path)

def upload_dwca(df_core, title, description, df_extension=None):
    archive = Archive()
    archive.eml_text = make_eml(title, description)
    core_table = Table(spec="https://rs.gbif.org/core/dwc_occurrence_2022-02-02.xml", data=df_core, id_index=0, only_mapped_columns=True)
    archive.core = core_table
    if df_extension:
        extension_table = Table(spec="https://rs.gbif.org/extension/dwc/measurements_or_facts_2022-02-02.xml", data=df_extension, id_index=0)
        archive.extensions.append(extension_table)

    file_name = datetime.now().strftime("output-%Y-%m-%d-%H%M%S") + '.zip'
    with tempfile.TemporaryDirectory() as temp_dir:
        local_path = os.path.join(temp_dir, file_name)
        archive.export(local_path)

        client = Minio(os.getenv('MINIO_URI'), access_key=os.getenv('MINIO_ACCESS_KEY'), secret_key=os.getenv('MINIO_SECRET_KEY'))
        upload_file(client, os.getenv('MINIO_BUCKET'), f"{os.getenv('MINIO_BUCKET_FOLDER')}/{file_name}", local_path)
        return f"https://{os.getenv('MINIO_URI')}/{os.getenv('MINIO_BUCKET')}/{os.getenv('MINIO_BUCKET_FOLDER')}/{file_name}"
