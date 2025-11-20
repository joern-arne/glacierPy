#!/usr/bin/env python3

import os
import sys
from . import lib
from InquirerPy import inquirer
import argparse
from typing import Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GlacierClientInquirer:
    """
    Interactive command-line interface for managing AWS Glacier vaults.
    """
    __vault: str | None

    def __init__(self, vault: str | None = None):
        """
        Initialize the GlacierClientInquirer.

        Args:
            vault (str | None): The name of the vault to manage. Defaults to None.
        """
        self.__vault = vault

    def run(self) -> None:
        """
        Runs the interactive interface.
        """
        self.__check_environment()

        while True:
            if not self.__vault:
                lib.print_vaults()
                self.__select_vault()

            assert self.__vault is not None
            lib.print_vault_state(self.__vault)
            action = self.__select_action()
            self.__vault = None

            if action == 'exit' or not inquirer.confirm(message="Would you like to continue with another vault?", default=True).execute():
                sys.exit()


    def __check_environment(self) -> None:
        """
        Checks if the necessary environment variables are set.
        Exits if AWS_PROFILE or AWS_REGION are missing.
        """
        if os.environ.get('AWS_PROFILE') is None:
            logger.error('Please configure your awscli and "export AWS_PROFILE=<PROFILE>" or use --profile in order to use glacierPy.')
            sys.exit(1)

        if os.environ.get('AWS_REGION') is None:
            logger.error('Please "export AWS_REGION=<REGION>" or use --region in order to use glacierPy.')
            logger.error('  e.g.: export AWS_REGION=eu-central-1')
            sys.exit(1)


    def __select_vault(self) -> None:
        """
        Prompts the user to select a vault from the available list.
        """
        choice = inquirer.select(
            message="Select a AWS Glacier Vault:",
            choices=[
                *[vault['VaultName'] for vault in lib.get_vaults()],
                *[{'name': 'EXIT', 'value': '__exit'}]
            ],
            default=None,
        ).execute()

        if choice == '__exit':
            sys.exit()
        else:
            self.__vault = choice


    def __select_action(self) -> Any:
        """
        Prompts the user to select an action to perform on the selected vault.

        Returns:
            Any: The selected action.
        """
        assert self.__vault is not None
        jobs = lib.get_jobs(self.__vault)

        vault_actions = []
        
        if jobs and jobs.get('JobList'):
            vault_actions = [
                {'name': f'Delete Inventory: {job["JobId"][:25]}', 'value': ('delete_inventory', job["JobId"])}
                for job in jobs['JobList']
                if job['Action'] == lib.JOB_ACTION_INVENTORY_RETRIEVAL
                and job['Completed']
                and job['StatusCode'] == lib.JOB_STATUS_SUCCEEDED
            ]

        choice = inquirer.select(
            message="Select an action:",
            choices=[
                *vault_actions,
                {'name': 'Retrieve Inventory', 'value': 'retrieve_inventory'},
                {'name': 'Delete Vault', 'value': 'delete_vault'},
                {'name': 'BACK', 'value': 'back'},
                {'name': 'EXIT', 'value': 'exit'}
            ],
            default=None,
        ).execute()

        if choice == 'retrieve_inventory':
            lib.retrieve_inventory(self.__vault)
        elif choice == 'delete_vault':
            lib.delete_vault(self.__vault)
        elif isinstance(choice, tuple) and choice[0] == 'delete_inventory':
            lib.delete_inventory(self.__vault, choice[1])
        
        return choice


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--vault', help='Choose vault')
    parser.add_argument('--report', help='Only print report info', action='store_true', default=False)
    parser.add_argument('--region', help='AWS Region')
    parser.add_argument('--profile', help='AWS Profile')
    args = parser.parse_args()

    if args.region:
        os.environ['AWS_REGION'] = args.region
    if args.profile:
        os.environ['AWS_PROFILE'] = args.profile
    
    args = parser.parse_args()

    if args.report:
        if args.vault:
            lib.print_vault_state(args.vault)
        else:
            lib.print_vaults()
    else:
        gci = GlacierClientInquirer(args.vault)
        gci.run()

if __name__ == '__main__':
    main()