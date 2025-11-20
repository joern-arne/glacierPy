import os
import json
import functools
import threading
import multiprocessing
from typing import Any
import textwrap

import botocore
import botocore.session
import botocore.exceptions
import concurrent.futures
from tqdm import tqdm
from tabulate import tabulate
import logging

logger = logging.getLogger(__name__)

# Constants
JOB_ACTION_INVENTORY_RETRIEVAL = 'InventoryRetrieval'
JOB_STATUS_SUCCEEDED = 'Succeeded'
JOB_TYPE_INVENTORY_RETRIEVAL = 'inventory-retrieval'
JOB_FORMAT_JSON = 'JSON'

__all__ = [
    'get_glacier_client',
    'get_vaults',
    'get_jobs',
    'retrieve_inventory',
    'delete_inventory',
    'delete_archive',
    'delete_vault',
    'print_vaults',
    'print_vault_state',
    'JOB_ACTION_INVENTORY_RETRIEVAL',
    'JOB_STATUS_SUCCEEDED',
]


@functools.lru_cache
def get_glacier_client() -> Any:
    """
    Creates and returns a cached boto3 glacier client.
    
    Returns:
        A botocore client for Glacier.
    """
    region = os.environ.get('AWS_REGION')
    session = botocore.session.get_session()
    return session.create_client('glacier', region_name=region)


def get_vaults() -> list[dict[str, Any]]:
    """
    Retrieves a list of available Glacier vaults.

    Returns:
        list[dict[str, Any]]: A list of dictionaries containing vault information.
    """
    try:
        return get_glacier_client().list_vaults()['VaultList']
    except botocore.exceptions.ClientError as e:
        logger.error(f"Failed to list vaults: {e}")
        raise


def get_jobs(vault_name: str) -> dict[str, Any]:
    """
    Retrieves a list of jobs for a specific vault.

    Args:
        vault_name (str): The name of the vault.

    Returns:
        dict[str, Any]: A dictionary containing job information.
    """
    try:
        return get_glacier_client().list_jobs(vaultName=vault_name)
    except botocore.exceptions.ClientError as e:
        logger.error(f"Failed to list jobs for vault {vault_name}: {e}")
        raise


def retrieve_inventory(vault_name: str) -> None:
    """
    Initiates an inventory retrieval job for the specified vault.

    Args:
        vault_name (str): The name of the vault.
    """
    try:
        get_glacier_client().initiate_job(
            vaultName=vault_name,
            jobParameters={
                'Format': JOB_FORMAT_JSON,
                'Type': JOB_TYPE_INVENTORY_RETRIEVAL,
                'Description': f'glacierPy-retrieve-inventory-{vault_name}'
            }
        )
        logger.info(f"Initiated inventory retrieval for vault: {vault_name}")
    except botocore.exceptions.ClientError as e:
        logger.error(f"Failed to initiate inventory retrieval for {vault_name}: {e}")
        raise


def delete_inventory(vault_name: str, jobid: str) -> None:
    """
    Deletes all archives listed in the inventory retrieved by the specified job.

    Args:
        vault_name (str): The name of the vault.
        jobid (str): The ID of the inventory retrieval job.
    """
    logger.info(f'Download inventory of job {jobid}')
    try:
        job_output = get_glacier_client().get_job_output(
            vaultName=vault_name,
            jobId=jobid,
        )
        archive_list = json.load(job_output['body'])['ArchiveList']
    except botocore.exceptions.ClientError as e:
        logger.error(f"Failed to get job output for {jobid}: {e}")
        raise

    logger.info(f'Delete {len(archive_list)} archives from vault...')

    with tqdm(total=len(archive_list)) as progress:
        tasks = set()
        with concurrent.futures.ThreadPoolExecutor() as tpe:
            for archive in archive_list:
                tasks.add(tpe.submit(delete_archive, vault=vault_name, archive_id=archive['ArchiveId']))

            for future in concurrent.futures.as_completed(tasks):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Failed to delete archive: {e}")
                progress.update(1)


def delete_archive(vault: str, archive_id: str) -> Any:
    """
    Deletes a single archive from a vault.

    Args:
        vault (str): The name of the vault.
        archive_id (str): The ID of the archive to delete.

    Returns:
        Any: The response from the delete_archive call.
    """
    try:
        response = get_glacier_client().delete_archive(
            vaultName=vault,
            archiveId=archive_id
        )
        return response
    except botocore.exceptions.ClientError as e:
        logger.error(f"Failed to delete archive {archive_id} from {vault}: {e}")
        raise


def delete_vault(vault_name: str) -> None:
    """
    Deletes a vault.

    Args:
        vault_name (str): The name of the vault to delete.
    """
    client = get_glacier_client()
    try:
        client.delete_vault(
            vaultName=vault_name
        )
        logger.info(f"Deleted vault: {vault_name}")
    except client.exceptions.InvalidParameterValueException:
        logger.warning(textwrap.dedent(f'''
            Can not delete vault {vault_name}.
            It seems the vault is not empty or the inventory is not up to date.
            If you have just deleted all archives contained in the vault please wait 24 hours
            or retrieve the current inventory and try again.
        '''))
    except botocore.exceptions.ClientError as e:
        logger.error(f"Failed to delete vault {vault_name}: {e}")
        raise


def print_vaults() -> None:
    """
    Prints a table of available vaults.
    """
    print(textwrap.dedent(f'''
        Available Vauls:
        ================
        {tabulate(get_vaults(), headers="keys")}
    '''))


def print_vault_state(vault_name: str) -> None:
    """
    Prints the state of a vault, including recent jobs.

    Args:
        vault_name (str): The name of the vault.
    """
    jobs = get_jobs(vault_name)['JobList']

    if jobs:
        print(textwrap.dedent(f'''
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
        '''))
    else:
        print(textwrap.dedent('''
            Jobs:
            =====
            No recent inventories. Please request the archive inventory to prepare
            the deletion of the archives and subsequently the vault. 
        '''))
