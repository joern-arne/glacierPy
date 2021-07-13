# glacierPy
A small AWS Glacier client to make the deletion of faults easier


# General process
The process is supported interactively by the tool.

1. Request to `Retrieve inventory` of vault.
2. Wait 3-5 hours until the inventory has been created.
3. `Delete inventory` (all archives) from the vault.
4. Wait another 3-5 hourse until the inventory has been updated at AWS.
5. Request to `Delete vault`to remove the vault completely.


# Setup
Clone this repository and use `make` to prepare and run the script.

```bash
# clone the repository
git clone https://github.com/joern-arne/glacierPy.git

# prepare python virtual environemt and install requirements
cd glacierPy
make
```

# Run
```bash
# run script via make
make run

# run script directly (supports parameters as described at "Usage")
venv/bin/python3 glacierPyInquirer.py
```

# Usage
```bash
usage: glacierPyInquirer.py [-h] [--vault VAULT] [--report]

optional arguments:
  -h, --help     show this help message and exit
  --vault VAULT  Choose vault
  --report       Only print report info
```