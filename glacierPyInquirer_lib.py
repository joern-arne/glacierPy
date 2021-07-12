import json
import functools
import threading
import botocore
import botocore.session
import concurrent.futures
import multiprocessing
from tqdm import tqdm
from pathlib import Path
from tabulate import tabulate

@functools.lru_cache
def get_glacier_client(_ = threading.current_thread(), region='eu-central-1'):
    session = botocore.session.get_session()
    return session.create_client('glacier', region_name=region)

def get_vaults():
    return get_glacier_client().list_vaults()['VaultList']

def get_jobs(vault_name):
    return get_glacier_client().list_jobs(vaultName=vault_name)

def retrieve_inventory(vault_name):
    get_glacier_client().initiate_job(
        vaultName=vault_name,
        jobParameters={
            'Format': 'JSON',
            'Type': 'inventory-retrieval',
            'Description': f'glacierPy-retrieve-inventory-{vault_name}'
        }
    )

def delete_inventory(vault_name, jobid):
    print(f'Download inventory of job {jobid}')
    job_output = get_glacier_client().get_job_output(
        vaultName=vault_name,
        jobId=jobid,
    )
    archive_list = json.loads(job_output['body'].read().decode("utf-8"))['ArchiveList']

    print(f'Delete {len(archive_list)} archives from vault...')

    with tqdm(total=len(archive_list)) as progress:
        parallelism = multiprocessing.cpu_count()
        tasks = set()
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallelism) as tpe:
            for archive in archive_list:
                tasks.add(tpe.submit(delete_archive, vault=vault_name, archive_id=archive['ArchiveId']))

            for future in concurrent.futures.as_completed(tasks):
                progress.update(1)

def delete_archive(vault, archive_id):
    response = get_glacier_client().delete_archive(
        vaultName=vault,
        archiveId=archive_id
    )
    return response

def delete_vault(vault_name):
    client = get_glacier_client()
    try:
            client.delete_vault(
            vaultName=vault_name
        )
    except client.exceptions.InvalidParameterValueException as err:
        print(f'''
Can not delete vault {vault_name}.
It seems the vault is not empty or the inventory is not up to date.
If you have just deleted all archives contained in the vault please wait 24 hours
or retrieve the current inventory and try again.
''')

def print_vaults():
    print(f'''
Available Vauls:
================
{tabulate(get_vaults(), headers="keys")}
''')

def print_vault_state(vault_name):
    jobs = get_jobs(vault_name)['JobList']

    if jobs:
        print(f'''
Inventories:
============
{tabulate([
    {
        k: str(v)[:25] for k, v in item.items() 
        if k in ('JobId', 'Action', 'CreationDate', 'Completed', 'StatusCode', 'CompletionDate', 'InventorySizeInBytes')
    }
    for item in jobs
], headers="keys")
}
''')
    else:
        print('''
Jobs:
=====
No recent inventories. Please request the archive inventory to prepare
the deletion of the archives and subsequently the vault. 
''')
