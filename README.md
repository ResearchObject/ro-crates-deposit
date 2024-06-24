# RO-Crates Data Deposit

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.8127644.svg)](https://doi.org/10.5281/zenodo.8127644)

Command line tool to deposit a [RO-Crate directory](https://www.researchobject.org/ro-crate/) to an [InvenioRDM](https://inveniordm.web.cern.ch/). 

## Requirements

- [`Python 3.x`](https://www.python.org/downloads/)

## Setup

### Create an InvenioRDM API token
1. Register for an account on your chosen InvenioRDM instance. [Zenodo Sandbox](https://sandbox.zenodo.org/) can be used for testing.
1. Go to your profile and select Applications.
1. You should see a section called "Personal access tokens." Click the "New token" button.
1. Give the token a name that reminds you of what you're using it for (e.g. RO-Crate upload token)
1. Select the scopes deposit:write and deposit:actions.
1. Click "Create."
1. Copy the access token and continue with the next stage.

![Screenshot of token creation page on TU Wien instance](./images/researchdata.png)

### Set up the environmental variables
1. copy and rename `.env.template` to `.env` in the same folder
1. open `.env` with a text editor and fill in your API key in the `INVENIORDM_API_KEY` variable
1. fill in the InvenioRDM base URL in the `INVENIORDM_BASE_URL` variable
  - in case of Zenodo Sandbox: use `https://sandbox.zenodo.org/`
  - in case of TU Wien test instance: use `https://test.researchdata.tuwien.ac.at/`
1. Run `source .env` to set the environment variables for the session

If you prefer to set the environment variables `INVENIORDM_API_KEY` and `INVENIORDM_BASE_URL` another way (e.g. in `~/.bashrc`), you can do that instead.

### Set up the Python environment
Run `python3 -m pip install -r requirements.txt`

## Usage

### General usage

Run `python3 deposit.py <ro-crate-dir>` with `<ro-crate-dir>` being the path to the RO-Crate directory. The record is saved as a draft and not published.

Run the same command with the `-p` option to publish the record.

Run `python3 deposit.py -h` for help.

### Manually verifying DataCite conversion before upload

This tool is a *best-effort* approach. After converting the metadata file, the resulting DataCite file is stored as `datacite-out.json` in the root directory. Users can adjust the generated DataCite file as needed, and can run the program in two stages to facilitate this:

First, run the program with the `--no-upload` option, to create the DataCite file without uploading anything to InvenioRDM:

`python3 deposit.py --no-upload <ro-crate-dir>`.

After verifying and adjusting the DataCite file, use the `-d` option to tell the program to use this file for upload and skip the process of conversion:

`python3 deposit.py -d <datacite-file> <ro-crate-dir>`.


### Further options

```
usage: deposit.py [-h] [-d DATACITE] [--no-upload] [-o] [-p] [-z] ro_crate_directory

Takes a RO-Crate directory as input and uploads it to an InvenioRDM repository

positional arguments:
  ro_crate_directory    Path to the RO-Crate directory to upload

options:
  -h, --help            show this help message and exit
  -d DATACITE, --datacite DATACITE
                        Path to a DataCite metadata file to use for the upload. Skips the conversion process from RO-Crate metadata to DataCite
  --no-upload           Stop before creating InvenioRDM record and do not upload files. Use this option to create a DataCite metadata file for manual
                        review
  -o, --omit-roc-files  Omit files named 'ro-crate-metadata.json' and directories/files containing 'ro-crate-preview' from the upload (not
                        recommended)
  -p, --publish         Publish the record after uploading
  -z, --zip             Instead of uploading all the files within the crate, create and upload a single zip file containing the whole crate
```

## File structure

The project consists of the following structure:

- `/mapping`: Contains code for the mapping process
  - `converter.py`: Python script used to map between RO-Crates and DataCite. Not to be called by the user.
  - `mapping.json`: Encodes the mapping between RO-Crates and DataCite. See [Mapping](#mapping) for more. 
  - `condition_functions.py`: Defines functions used for the mapping. See [Conditon Functions](#condition-functions) for more.
  - `processing_functions.py`: Defines functions used for the mapping. See [Processing Functions](#processing-functions) for more.
- `/upload`: Contains code for the upload process
  - `uploader.py`: Python script used to upload the files to the InvenioRDM. Not to be called by the user.
- `deposit.py`: Starting point. Used to map and upload the RO-Crate directory.
- `.env.template`: Template file for the environment variables.
- `/test`: contains tests and test data

## Mapping

The project aims at decoupling the definition of the mapping between RO-Crates and DataCite from code. This means, that users can quickly change/add/remove mapping rules without code changes. 

The mapping is implemented in `/mapping/converter.py`. The mapping rules are defined in `/mapping/mapping.json`. Processing functions and condition functions are defined in `/mapping/processing_functions.py` and `condition_functions.py`, respectively. A textual description including shortcomings and assumptions of the mapping can be found in [mapping-notes.md](./mapping-notes.md).

### Mapping format

The mapping is defined in `/mapping/mapping.json` and consists of **Mapping Collections** and **Mapping Rules**.

#### Mapping Collections

A Mapping Collection bundles different mapping rules together, e.g. rules that define the mapping between `author` in RO-Crates and `creators` in DataCite. Each mapping collection contains the following keys:

| Key    |  Description |    Possible values | Mandatory?  |
|---------------|-------------- | ---------------  |-------------|
| `mappings`   |  contains the mapping rules   |  mapping rules          | yes (unless `_ignore` is present)         |
| `_ignore`     |  ignores the mapping rule if present     | any  | no   |
| `ifNonePresent` | in case no mapping rule is applied, the value defined here is applied | see below | no

##### `ifNonePresent`

`ifNonePresent` can be used to specify what happens if no Mapping Rule of the defined Mapping Rules in the current Mapping Collection is applied. The value of the field is an array of the following form: 

```json
{
  "<to_query>": "<value>"
}
```

In case no Mapping Rule is applied, the value specified in `<value>` is applied to the field defined by `<to_query>` in the DataCite.

#### Mapping Rules

A Mapping Rule defines which fields from RO-Crates are mapped to which fields in DataCite.

Each rule may contain the following keys:


| Key    |  Description |    Possible values | Mandatory?  |
|---------------|-------------- | ---------------  |-------------|
| `from`   |  defines the source in the RO-Crates file   |  query string (see below)          | yes         |
| `to`     |  defines the target in the DataCite file     | query string (see below)        | yes         |
| `value`  | allows value transformations | may be a string, array, or object | no |
| `processing` | uses a processing function | string starting with `$` and referencing an existing processing function | no |
| `onlyIf` | uses a condition function | string starting with `?` and referencing an existing condition function | no |    
| `_ignore` | ignores the rule if present | any | no |    

#### `from` and `to` querying

To define the mapping between RO-Crates and DataCite, it is necessary to specify which field in RO-Crates is mapped to which field in DataCite. This is achieved by specifying the `from` and `to` fields in a Mapping Rule.

**Example**

Given the following RO-Crates metadata file:

```json
{
    "@context": "https://w3id.org/ro/crate/1.1/context", 
    "@graph": [
        {
            "@type": "CreativeWork",
            "@id": "ro-crate-metadata.json",
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
            "about": {"@id": "./"}
        },  
        {
            "@id": "./",
            "@type": "Dataset",
            "name": "Name",
            "author": {"@id": "https://orcid.org/0000-0002-8367-6908"}
        },
        {
            "@id": "https://orcid.org/0000-0002-8367-6908",
            "@type": "Person",
            "name": "J. Xuan"
        }
    ]
}
```

Speficifying the `title` field is achieved with `title`. In case the value of a key refers to another object, such as in the case of authors, querying is done using the `$` charater. Refering to the `name` field of an `author` is done using `$author.name`. It is important to note, that the `author` field may be an array. Therefore, it is necessary to mark this as a possible array. Refering to this value can be done by using the `[]` characters, i.e., `$author[].name`.

Specifying the DataCite field is done in a similar fashion.



#### Processing functions

Processing functions are functions that are applied to the raw source value extracted from the RO-Crates metadata file. When a processing function wants to be applied to a mapping rule, the `processing` entry is assigned the value `$<function_name>`. The function then needs to be implemented in `/mapping/processing_functions.py`. 

**Example**

Given is the following mapping of the author type:

```json
"person_or_org_type_mapping": {
    "from": "$author.@type",
    "to": "metadata.creators[].person_or_org.type",
    "processing": "$authorProcessing"
}
```

The value `Person` in the RO-Crates metadata file should be mapped to the value `personal`. Also, the value `Organization` should be mapped to the value `organizational`. The function `authorProcessing` can now be implemented in `/mapping/processing_functions.py` to achieve this logic. Note that the value of the `processing` key in the mapping rule and the function name need to coincide:

```py
def authorProcessing(value):
    if value == "Person":
        return "personal"
    elif value == "Organization":
        return "organizational"
    else:
        return ""
```


#### Condition functions

Condition functions are similar to processing functions. Condition functions can be used to restrict when a mapping rule should be executed. The mapping is executed, if the function defined in the `onlyIf` key returns true.

**Example**

The mapping of DOI identifiers looks as follows:

```json
"alternate_mapping": {
  "from": "identifier",
  "to": "metadata.identifiers[]",
  "value": {
      "scheme": "doi",
      "identifier": "@@this"
  },
  "processing": "$doi_processing",
  "onlyIf": "?doi"
}
```

The mapping should only be executed, if the value in the `identifier` field in the RO-Crates metadata file is indeed a DOI identifier. This check can be achieved by defining the `doi` function in `/mapping/condition_functions.py`. Note that the value of the `onlyIf` key in the mapping rule and the function name need to coincide:

```py
def doi(value):
    return value.startswith("https://doi.org/")
```


#### Value formatting

A value can also be formatted, e.g. as needed when a value in RO-Crate needs to be transformed to another value in DataCite. Although this can also be achived using a processing function, value transformations provide an easier alternative. Every occurence of `@@this` is replaced by the source value.

**Example**

Given the following mapping rule:
```json
"languages_mapping_direct": {
  "from": "inLanguage",
  "to": "metadata.languages[]",
  "value": {
    "id": "@@this"
  }
}
```

The RO-Crate entry 
```json
...
"inLanguage": "en"
...
```

is transferred into 

```json
"metadata": {
  "languages": [
    {
      "id": "en"
    }
  ]
}
```

#### Flow

This figure illustrates how the functions that are applied in a mapping rule.

![](./images/mapping_rule_flow.svg)

## Results


### Minimal RO-Crate

The result of uploading the minimal RO-Crate as shown on [https://www.researchobject.org/ro-crate/1.1/root-data-entity.html#minimal-example-of-ro-crate](https://www.researchobject.org/ro-crate/1.1/root-data-entity.html#minimal-example-of-ro-crate) ([`/test/minimal-ro-crate`](./test/minimal-ro-crate/)) leads to the following result:

![](./images/ro-crate-minimal-result.png)


### Optimal RO-Crate

The result of uploading the [`/test/test-ro-crate`](./test/test-ro-crate/) directory looks like this in TUW's InvenioRDM repository:

![](./images/result.png)

### Real World RO-Crate

We tested the tool on a real-world RO-Crate ([https://reliance.rohub.org/b927e3d8-5bfd-4332-b14c-ab3a07d36dc6?activetab=overview](https://reliance.rohub.org/b927e3d8-5bfd-4332-b14c-ab3a07d36dc6?activetab=overview)). The result is shown below:

![](./images/real-world-example.png)
