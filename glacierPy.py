#!/usr/bin/env python3

import os
import sys
import glacierPy_lib as lib
from InquirerPy import inquirer
import argparse

class GlacierClientInquirer:
    __vault: str

    def __init__(self, vault=None):
        self.__vault = vault

    def run(self):
        self.__check_environment()

        while True:
            if not self.__vault:
                lib.print_vaults()
                self.__select_vault()

            lib.print_vault_state(self.__vault)
            action = self.__select_action()
            self.__vault = None

            if action == 'exit' or not inquirer.confirm(message="Would you like to continue with another vault?", default=True).execute():
                sys.exit()


    def __check_environment(self):
        if os.environ.get('AWS_PROFILE') is None:
            print('Please configure your awscli and "export AWS_PROFILE=<PROFILE>" in order to use glacierPy.')
            sys.exit()

        if os.environ.get('AWS_REGION') is None:
            print('Please "export AWS_REGION=<REGION>" in order to use glacierPy.')
            print('  e.g.: export AWS_REGION=eu-central-1')
            sys.exit()


    def __select_vault(self):
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


    def __select_action(self):
        jobs = lib.get_jobs(self.__vault)

        vault_actions = list()
        
        if jobs and len(jobs['JobList']) > 0:
            for job in jobs['JobList']:
                if job['Action'] == 'InventoryRetrieval' \
                    and job['Completed'] == True \
                    and job['StatusCode'] == 'Succeeded':
                    vault_actions.append({'name': f'Delete Inventory: {job["JobId"][:25]}', 'value': ('delete_inventory', job["JobId"])})

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
        elif choice[0] == 'delete_inventory':
            lib.delete_inventory(self.__vault, choice[1])
        
        return choice


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--vault', help='Choose vault')
    parser.add_argument('--report', help='Only print report info', action='store_true', default=False)
    args = parser.parse_args()

    if args.report:
        if args.vault:
            lib.print_vault_state(args.vault)
        else:
            lib.print_vaults()
    else:
        gci = GlacierClientInquirer(args.vault)
        gci.run()