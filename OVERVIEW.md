# Overview

I’m creating a data standardisation chatbot system to help field biologists and ecologists with no knowledge of data science/management publish biodiversity data to [gbif.org](http://gbif.org) using the Darwin Core format. 

It should convert messy spreadsheets made by non technical users into darwin core standardised csvs. It does this by running through a series of pre-set Tasks, which it runs on either all the tables in the spreadsheet, or each table one by one. Here are the tasks:

```yaml
- model: api.task
  fields:
    name: extract_subtables
    per_table: true
    attempt_autonomous: true
    text: |-
      Step 1: 
      ~
      Separate out any sub tables in this dataframe into new, separate Tables. 
      Non-technical users squeeze two or more tables into one spreadsheet, which then gets loaded as a single table into the system. 
      A single table should be one block of related data with consistent columns and rows, any summary/total rows can be discarded. 
      IMPORTANT: Start by using the BasicExtractEmptyBoundaryTables method, which is a very simple function which splits up data based on empty rows and columns, but *DO NOT* rely on it. 
      Double check the Table snapshots, use your intelligence, ask the user if you cannot confidently make a guess at something, look at the first few rows, the last few rows, search for pattern breaks, etc. Often users add arbitrary and unnecessary columns like numbering or horizontal dividers. 
      NOTE: This is a challenging task, think it through clearly and carefully, step by step. 

      Finally: BE CAREFUL! It's very easy to separate out tables and lose information from columnns or rows. Before doing any table extraction, compare the old table with the new tables, and check to see if you are missing anything. 

      Here is an example of a particularly bad user-uploaded spreadsheet: 
      | WP2, 64 µm mesh (ind m-3)                       |                     |                     |            |            |       |         | Svartnes 2018 (ind m-3)        |            |
      | ----------------------------------------------- | ------------------- | ------------------- | ---------- | ---------- | ----- | ------- | ------------------------------ | ---------- |
      | Date                                            | 2017                | 2017                | 2018       | 2018       |       |         | WP2, 64 µm mesh                |            |
      | Sample/Net number                               | AVERAGE 20-21.02.17 | AVERAGE 20-21.02.17 | 12.06.2018 | 12.06.2018 |       |         | Date                           | 12.06.2018 | 12.06.2018 |
      | Layer [m]                                       | 50-0 m              | 170-50 m            | 50-0 m     | 170-50 m   |       |         | Sample/Net number              | WP2/64     | WP2/64 |
      | Calanus spp.                                    | 128                 | 259                 | 194        | 562        |       |         | Layer [m]                      | 170-50 m   | 50-0 m |
      | Microcalanus spp.                               | 471                 | 707                 | 16         | 125        |       |         | Calanus spp.                   | 562        | 194 |
      | Cyclopoida nauplii                              | 8724                | 9                   | 8061       | 2          |       |         | Microsetella norvegica nauplii | 110        | 3199 |
      | Fritillaria borealis                            | 5560                | 2                   | 0          | 0          |       |         | Cyclopoida nauplii             | 2          | 8061 |
      | Rotatoria                                       | 607                 | 25                  | 0          | 0          |       |         | Fritillaria borealis           | 0          | 0 |
      | SUM Others                                      | 16721               | 84                  | 223        | 32         |       |         | Rotatoria                      | 0          | 0 |
      |                                                 |                     |                     |            |            |       |         | SUM Others                     | 32         | 223 |
      | Total abundance                                 | 32211               | 1085                | 8495       | 721        |       |         |                                |            |  |
      | Total abundance without nauplii                 | 23487               | 1076                | 433        | 719        |       |         |                                |            |  |
      | Total copeods                                   | 599                 | 966                 | 210        | 687        |       |         |                                |            |  |
      |                                                 |                     |                     |            |            |       |         |                                |            |  |
      | % Microsetella of total zoopl (without nauplii) | #REF!               | #REF!               | #REF!      | #REF!      |       |         |                                |            |  |
      | % Microsetella of total copepods                | #REF!               | #REF!               | #REF!      | #REF!      |       |         |                                |            |  |
      |                                                 |                     |                     |            |            |       |         |                                |            |  |
      | ind/m3                                          |                     |                     |            |            |       |         |                                |            |  |
      | 19/06/2017                                      | M                   | F                   | CIV-CV     | CI-CIII    | SUM   | Nauplii |                                |            |  |
      | 0                                               | 200                 | 4880                | 80         | 160        | 5320  | 3080    |                                |            |  |
      | 10                                              | 622                 | 49518               | 498        | 1493       | 52131 | 33281   |                                |            |  |
      | 20                                              | 1991                | 38818               | 373        | 498        | 41680 | 6096    |                                |            |  |
      | 50                                              | 2280                | 3120                | 80         | 240        | 5720  | 200     |                                |            |  |
      | 90                                              | 600                 | 1720                | 160        | 120        | 2600  | 200     |                                |            |  |
      | 120                                             | 280                 | 1160                | 80         | 320        | 1840  | 1200    |                                |            |  |
      | ind/m3                                          |                     |                     |            |            |       |         |                                |            |  |
      | 21/06/2017                                      | M                   | F                   | CIV-CV     | CI-CIII    | SUM   | Nauplii |                                |            |  |
      | 0                                               | 0                   | 1440                | 0          | 120        | 1560  | 7800    |                                |            |  |
      | 10                                              | 2400                | 40320               | 480        | 1200       | 44400 | 19440   |                                |            |  |
      | 20                                              | 3000                | 17280               | 0          | 360        | 20640 | 4680    |                                |            |  |
      | 50                                              | 440                 | 1160                | 0          | 0          | 1600  | 80      |                                |            |  |
      | 90                                              | 120                 | 1040                | 0          | 0          | 1160  | 120     |                                |            |  |
      | 120                                             | 40                  | 240                 | 0          | 0          | 280   | 40      |                                |            |  |
      |                                                 |                     |                     |            |            |       |         |                                |            |  |

      This should be 4 tables, with the tables with Sum/Total rows discarded. 
      
      Table A:
      | WP2, 64 µm mesh (ind m-3) |                     |                     |            |            |
      | ------------------------- | ------------------- | ------------------- | ---------- | ---------- |
      | Date                      | 2017                | 2017                | 2018       | 2018       |
      | Sample/Net number         | AVERAGE 20-21.02.17 | AVERAGE 20-21.02.17 | 12.06.2018 | 12.06.2018 |
      | Layer [m]                 | 50-0 m              | 170-50 m            | 50-0 m     | 170-50 m   |
      | Calanus spp.              | 128                 | 259                 | 194        | 562        |
      | Microcalanus spp.         | 471                 | 707                 | 16         | 125        |
      | Cyclopoida nauplii        | 8724                | 9                   | 8061       | 2          |
      | Fritillaria borealis      | 5560                | 2                   | 0          | 0          |
      | Rotatoria                 | 607                 | 25                  | 0          | 0          |
      | SUM Others                | 16721               | 84                  | 223        | 32         |

      Table B:
      | Svartnes 2018 (ind m-3)        |            |
      | ------------------------------ | ---------- |
      | WP2, 64 µm mesh                |            |
      | Date                           | 12.06.2018 | 12.06.2018 |
      | Sample/Net number              | WP2/64     | WP2/64 |
      | Layer [m]                      | 170-50 m   | 50-0 m |
      | Calanus spp.                   | 562        | 194 |
      | Microsetella norvegica nauplii | 110        | 3199 |
      | Cyclopoida nauplii             | 2          | 8061 |
      | Fritillaria borealis           | 0          | 0 |
      | Rotatoria                      | 0          | 0 |
      | SUM Others                     | 32         | 223 |

      Table C:
      | ind/m3     |      |       |        |         |       |         |
      | ---------- | ---- | ----- | ------ | ------- | ----- | ------- |
      | 19/06/2017 | M    | F     | CIV-CV | CI-CIII | SUM   | Nauplii |
      | 0          | 200  | 4880  | 80     | 160     | 5320  | 3080    |
      | 10         | 622  | 49518 | 498    | 1493    | 52131 | 33281   |
      | 20         | 1991 | 38818 | 373    | 498     | 41680 | 6096    |
      | 50         | 2280 | 3120  | 80     | 240     | 5720  | 200     |
      | 90         | 600  | 1720  | 160    | 120     | 2600  | 200     |
      | 120        | 280  | 1160  | 80     | 320     | 1840  | 1200    |

      Table D:
      | ind/m3     |      |       |        |         |       |         |
      | ---------- | ---- | ----- | ------ | ------- | ----- | ------- |
      | 21/06/2017 | M    | F     | CIV-CV | CI-CIII | SUM   | Nauplii |
      | 0          | 0    | 1440  | 0      | 120     | 1560  | 7800    |
      | 10         | 2400 | 40320 | 480    | 1200    | 44400 | 19440   |
      | 20         | 3000 | 17280 | 0      | 360     | 20640 | 4680    |
      | 50         | 440  | 1160  | 0      | 0       | 1600  | 80      |
      | 90         | 120  | 1040  | 0      | 0       | 1160  | 120     |
      | 120        | 40   | 240   | 0      | 0       | 280   | 40      |

      ~ 
      Step 2: 
      ~

      Carefully look at each of the Tables you've created. Do any of them contain the same data and belong together? Should any rows be restructured as columns? In the previous example, Tables A & B belong together, as do Tables C and D. Table AB should look like this: 

      Table AB:

      | Sample details                 | 20-21.02.2017 (50-0 m) | 20-21.02.2017 (170-50 m) | 12.06.2018 (50-0 m) | 12.06.2018 (170-50 m) | Svartnes 12.06.2018 (50-0 m) | Svartnes 12.06.2018 (170-50 m) |
      | ------------------------------ | ---------------------- | ------------------------ | ------------------- | --------------------- | ---------------------------- | ------------------------------ |
      | Calanus spp.                   | 128                    | 259                      | 194                 | 562                   | 194                          | 562                            |
      | Microcalanus spp.              | 471                    | 707                      | 16                  | 125                   | 16                           | 125                            |
      | Pseudocalanus spp.             | 730                    | 35                       | 31                  | 20                    | 31                           | 20                             |
      | Metridia longa                 | 31                     | 209                      | 6                   | 38                    | 6                            | 38                             |
      | Acartia longiremis             | 768                    | 1                        | 273                 | 0                     | 273                          | 0                              |
      | Microsetella norvegica         | 9889                   | 620                      | 8118                | 263                   | 8118                         | 263                            |
      | Oithona similis                | 3510                   | 13                       | 1430                | 3                     | 1430                         | 3                              |
      | Other copepods                 | 108                    | 12                       | 3                   | 3                     | 3                            | 3                              |
      | Calanoida nauplii              | 3525                   | 19                       | 204                 | 59                    | 204                          | 59                             |
      | Microsetella norvegica nauplii | 7181                   | 78                       | 3199                | 110                   | 3199                         | 110                            |
      | Cyclopoida nauplii             | 8724                   | 9                        | 8061                | 2                     | 8061                         | 2                              |
      | Fritillaria borealis           | 5560                   | 2                        | 0                   | 0                     | 0                            | 0                              |
      | Rotatoria                      | 607                    | 25                       | 0                   | 0                     | 0                            | 0                              |
      
      Note that: 
      - The headers, which spanned over multiple rows, have been flattened, combined and standardised
      - Superfluous information which can be derived elsewhere, such as the year which can be derived from the collection dates, have been discarded. 

    additional_function: BasicExtractEmptyBoundaryTables

- model: api.task
  fields:
    name: join_tables
    per_table: false
    attempt_autonomous: false
    text: |-
      Carefully look at all of the Tables and decide if any contain the same data and belong together. Quite often users split up data by location or taxonomic group, for example. What we're aiming for is a single Table for all of the same sort of data - for example all species observations or species names should go into a single Table. Look for patterns in the different Tables, tell yourself about the data content of each Table, think about this critically and analytically. Users are human, illogical and unreliable - they may name and order column headings differently from one Table to the next, so you need to be on your toes with this one.

- model: api.task
  fields:
    name: rename_columns
    per_table: true
    attempt_autonomous: false
    text: |-
      When users publish data, they often create spreadsheets with cryptic information as they tend to write things with only themselves in mind. This task is a first pass to clarify what actual data we have in the spreadsheet.
      Take a deep breath, and think this through step-by-step.
      -
      Aim 1: examine the data presented in this table carefully: 
      a) Are the column heading meanings clear and reflecting the data in each column? Note that users sometimes make multiple header rows - if you notice this you can go ahead and flatten them first.
      b) If any of the first few columns are row headings (i.e. this is ia pivot table of some kind), do you understand what the values in there mean? Should they be renamed?
      Engage in conversation with the user to clarify anything that is ambiguous or that you don't understand. Make some intelligent guesses and fix things up as best you can, but ask the user if there's anything you're not reasonably confident of. 
      -
      Aim 2: once you have a good understanding of the column headings and data, rename columns (and/or data values) to make them immediately understandable. 
      -
      Aim 3: drop any unnecessary rows and columns containing data which has been derived from primary data. Particularly, look out for SUM/TOTAL rows at the bottom of the dataframe, and SUM/TOTAL columns at the end of it. If there are any other rows or columns which are not necessary or seem meaningless, remove those too.
      IMPORTANT: Be extremely careful when dropping rows or columns because of nan/None values, usually these contain important data even if the value is None. Look critically at the rows you plan to delete BEFORE you delete them, and check that they really are unnecessary. 
      -
      Aim 4: explain any confusing aspects of the data/structure by adding a short explanation to the dataset Description using the SetBasicMetadata function. 

      To achieve these four aims, start by asking the user one question at a time, based on the data in the table. Wait for the user's response before asking the next question.
      To achieve the desired conversational flow, here is an example of how the interaction should look:

      Agent: Does the first column ('S') mean species?
      User: Yes
      Agent: [runs Python function to rename column]
      Agent: I see. So does the next column contain the number of species you found?
      User: No, that's the measurement of ocean salinity where we took samples
      Agent: [runs Python function to rename column]
      Agent: So the numbers in the next columns all look similar, are these counts of individual species found? Is each column a different location/sample spot?  
      User: Yes, well sort of, it's actually %biomass of each species at different sites
      Agent: [runs Python function to rename column]
      Agent: [Calls SetBasicMetadata and sets dataset Description to: "Table ID 82 is wide format/pivot table with %biomass of species for different sample sites. NB the first column contains ocean salinity. "]
  additional_function: SetBasicMetadata

- model: api.task
  fields:
    name: set_basic_metadata
    per_table: false
    attempt_autonomous: false
    text: |-
      Examine the data presented in these tables carefully and the current dataset Description (a draft with some information about columns and data structure), and use it to derive a very short but descriptive draft Title (max 50 words) and Description (approx 3-5 sentences) for the dataset as a whole. Incorporate the current dataset Description and keep information about the columns and data structure at the end of the Description. But you can ignore the data structure in sheets - that will change, just focus on the contents of the data. Ask the user to improve your Title and Description, and finalise in consultation with them before saving to the database using SetBasicMetadata.
    additional_function: SetBasicMetadata

- model: api.task
  fields:
    name: check_data_suitability
    per_table: false
    attempt_autonomous: false
    text: |-
      GBIF.org is a global database for biodiversity data. Suitable data for publication includes:
      - Species Occurrence Data and Sampling Event Data: Records of WHEN and WHERE a species (WHAT) was observed, and often by WHO (collector, citizen scientist, researcher, etc) - these may also be e.g. eDNA data even if the species identification only occurs at a higher taxonomic level.
      - Checklists: Lists of species found in a specific area or ecosystem.
      Look at this data and the metadata description critically. 
      Is this data suitable for publication on gbif.org? If it is, mark this Task as complete, otherwise let the user know and reject the the dataset using the RejectDataset function. 
    additional_function: RejectDataset

- model: api.task
  fields: 
    name: delete_unnecessary_tables
    per_table: false
    attempt_autonomous: true
    text: >
      Delete any tables which are not primary data - i.e. which can be derived from other tables. If the data is cryptic or the column headers are not obvious check with the user before doing a deletion. 

- model: api.task
  fields:
    name: flatten_headers
    per_table: true
    attempt_autonomous: true
    text: >
      Flatten any of the top rows which you think might contain header information into a single row, and convert it to the dataframe header. If there are multiple candidate header rows, try to preserve as much information as possible when you merge them. 
    
- model: api.task
  fields:
    name: de_crosstab  # Convert crosstab/pivot to long.
    per_table: true
    attempt_autonomous: true
    text: >  
      Is this table in crosstab or pivot format? Often users have a crosstab of species x locations, with the value cells being individualCount or organismQuantity. If this is the case, convert the crosstab to long format, label the new column accordingly and present it to the user for confirmation. Don't forget to save changes to the database before marking this Task as complete.
    
- model: api.task
  fields:
    name: set_core_and_extensions
    per_table: false
    attempt_autonomous: false
    text: |-
      Carefully examine the contents of each of these dataframes. They need to be combined together into a single Darwin Core archive, with one core table (Event, Occurrence or Checklist), with optional extension Tables. Decide on 1) either an Occurrence, Event + Occurrence, or Checklist (taxonomy) DwC core, and 2) optionally any DwC extension for this dataset, the most commonly used one is MeasurementOrFact.
      Common Event DwC fields (can also be included in an Occurrence core Table):
       - eventDate (must be ISO format)
       - locality
       - minimumElevationInMeters
       - maximumElevationInMeters
       - country
       - decimalLatitude
       - decimalLongitude
       - fieldNotes
      Common Occurrence DwC fields: 
       - recordedBy (collector/observer's name)
       - recordedByID (often ORCID)
       - scientificName
       - kingdom
       - individualCount or organismQuantity/organismQuantityType (IMPORTANT: This is where abundance or number/counts of individuals go, NOT in MeasurementOrFact)
       - occurrenceRemarks
      Common Checklist DwC fields
       - taxonID
       - scientificName
       - kingdom
       - taxonRemarks
      NOTE 1: If this is not a Taxonomy/Checklist, you must use the Occurrence core by default and only use a separate table as an Event core if the data contains multiple Occurrences that can be easily grouped (like a series of observations across different times and locations within the same project). If the data is simple, it's easier to combine Event and Occurrence fields into a single Table. In the majority of cases just using the single Occurrence core + some Event fields is easiest. 
      NOTE 2: The MeasurementOrFact extension should be used to store facts or measurements which do not fit into the core fields or where there are multiple measurements per field. Examples: length, weight, temperature, salinity, age, growth rate, symbiotic relationships, predator-prey interactions, etc. DO NOT use it for individual counts or abundance, those numbers should go into individualCount or organismQuantity/organismQuantityType.
      NOTE 3: In almost all cases, if you are publishing Event/Occurrence data, you should discard any Tables containing taxonomy information only that a user may have gathered - that should not get published. 

      Your task is now to: 
      1) Discuss your recommendations for DwC core and extensions with the user, note that extensions are optional
      2) Rename the columns in the Tables to DwC fields (see above for common fields), if column data/names are cryptic and difficult to understand, ask the user about them
      3) Organize the Tables, joining or deleting dataframes as necessary so the data structure resembles what is required
      3) Add a very short (max 3 sentences) summary to the dataset description, detailing why you and the user have chosen this DwC core + any extensions, use SetBasicMetadata to save it and be careful not to overwrite the description already saved.
      4) Call the SetAgentTaskToComplete function and move on to the next task
    additional_function: SetBasicMetadata

- model: api.task
  fields:
    name: unique_ids
    per_table: true
    attempt_autonomous: true
    text: >  
      Ensure that every row for each Table has a unique identifier (e.g. occurrenceID, eventID, measurementID, etc). If there isn't an obvious one present, generate uuids.

- model: api.task
  fields:
    name: validation
    per_table: true
    attempt_autonomous: true
    text: >  
      Check each of the columns (which should all be darwin core fields) for validation errors. Pay particular attention to dates, and get these in the right column. Additionally, check the required fields for each DwC core and DwC extension, and make sure they are present. 

- model: api.task
  fields:
    name: image_urls
    per_table: true
    attempt_autonomous: false
    text: >  
      This is only really necessary for Occurrence or Event datasets (not Taxon). Determine if the user wishes to publish any images associated with the occurrences in their dataset, and if they do explain the images need to be hosted online prior to dataset publication. Suggest a scientific repository such as Zenodo to upload the images, and explain that the URLs must be put in an associatedMedia column as an extra step after this process is complete. If the image URLs are present already, make sure the column is correctly named and in the right Table.

- model: api.task
  fields:
    name: adhoc
    per_table: false
    attempt_autonomous: false
    text: >  
      Carefully inspect these preprocessed dataframes. They should be nearly ready for publication. Are there any other outstanding issues you can see? Fix these and mark your Task as complete when you think there are no more issues and the dataframes are ready for publication.
```

Each Task starts a new conversation/Message Set with GPT-4. The first message generated is a System Message, which is made from a template which includes the Task text, some contextual information about the user’s spreadsheet tables. Every Message Set which gets sent to GPT4 also tells GPT-4 it has access to certain functions, the main two are:

```python

class Python(OpenAIBaseModel):
    """
    Run python code using `exec(code, globals={'Dataset': Dataset, 'Table': Table, 'pd': pd, 'np': np}, {})`, i.e. with access to pandas (pd), numpy (np), and a Django database with models `Table` and `Dataset`
    E.g. `df_obj = Table.objects.get(id=df_id); print(df_obj.df.to_string());`
    Notes: - Edit, delete or create new Table objects as required - remember to save changes to the database (e.g. `df_obj.save()`). 
    - Use print() if you want to see output - Output is a string of stdout, truncated to 2000 characters 
    - IMPORTANT NOTE #1: State does not persist - Every time this function is called, the slate is wiped clean and you will not have access to any objects created previously.
    - IMPORTANT NOTE #2: If you merge or create a new Table based on old Tables, tidy up after yourself and delete any irrelevant/out of date Tables.
    """
    code: str = Field(..., description="String containing valid python code to be executed in `exec()`")

    def run(self):
        code = re.sub(r"^(\s|`)*(?i:python)?\s*", "", self.code)
        code = re.sub(r"(\s|`)*$", "", code)
        old_stdout = sys.stdout
        new_stdout = StringIO()
        sys.stdout = new_stdout
        result = ''
        try:
            from api.models import Dataset, Table

            locals = {}
            globals = { 'Dataset': Dataset, 'Table': Table, 'pd': pd, 'np': np, 'uuid': uuid }
            exec(code, globals, locals)
            stdout_value = new_stdout.getvalue()
            
            if stdout_value:
                result = stdout_value
            else:
                result = f"Executed successfully without errors."
        except Exception as e:
            result = repr(e)
        finally:
            sys.stdout = old_stdout
        return f'`{code}` executed, result: {str(result)[:2000]}'

class SetAgentTaskToComplete(OpenAIBaseModel):
    """Mark an Agent's task as complete"""
    agent_id: PositiveInt = Field(...)

    def run(self):
        from api.models import Agent
        try:
            agent = Agent.objects.get(id=self.agent_id)
            agent.completed_at = datetime.now()
            agent.save()
            print('Marking as complete...')
            return f'Task marked as complete for agent id {self.agent_id} .'
        except Exception as e:
            return repr(e)[:2000]

```

## Sequence of events

1. GPT-4o API is sent a System Message with a prompt for each Task
2. It replies with Assistant Messages for the user (typically asking for more information if required) or with Function Messages - calling functions it has access to.
    1. Assistant Messages are stored in a Message Set for that Task and sent to the user, the user’s reply is stored as a User Message in the Message Set and sent back to GPT-4, this repeats until GPT-4 replies with a Function Message 
    2. Function Message replies from GPT-4 are actually run as functions in the codebase (either Python or SetAgentTaskToComplete) and not stored in the Message Set. GPT-4 returns a function name, and I use getattr to get the actual corresponding function in the code. Function arguments are also returned as JSON arguments which can get passed into the function as it is run. 
    3. The RESULTS of the function that is called is added to a new Function Message, which is stored in the Message Set. If a Function Message calls the “SetAgentTaskToComplete” function the system marks that Task as complete in the UI and moves on to the next Task. If a Function Message calls the “Python” function, GPT-4 generated python code from the arguments is passed to a function which runs the code in a sandbox, and returns the output of what was executed. This repeats until SetAgentTaskToComplete is called.

## The problem

I have several real world examples of messy spreadsheets, and GPT-4o is failing to correctly format any of them. For example: 

|                       |                 |                            | Jetties      | Vertical walls |
| --------------------- | --------------- | -------------------------- | ------------ | -------------- |
| Developmental stage   | Family          | Taxon                      | Total number | Jetty B        | Jetty D | Total % | Total number | Spithead | Francis Drake | Total % |
| Invertebrates (Traps) |
| Zoea                  | Pinnotheridae   | Pinnotheres sp.            | 2561697      | 9.6152         | 84.3818 | 93.9971 | 792 | 10.05 | 17.58 | 27.62 |
|                       | Pinnotheridae   | Pinnixa sp.                | 1284         | 0.0096         | 0.0375 | 0.0471 | 3 | 0.03 | 0.07 | 0.10 |
|                       | Leucosiidae     |                            | 171          | 0.0026         | 0.0037 | 0.0063 | 23 | 0.66 | 0.14 | 0.80 |
| Megalopa              | Pinnotheridae   | Pinnotheres sp.            | 1692         | 0.0348         | 0.0273 | 0.0621 | 742 | 21.90 | 3.98 | 25.88 |
|                       | Hymenosomatidae | Hymenosoma orbiculare      | 862          | 0.0137         | 0.0179 | 0.0316 | 186 | 3.84 | 2.65 | 6.49 |
|                       |                 | Unidentified megalopa sp.5 | 0            | 0              | 0 | 0 | 1 | 0.03 | 0.00 | 0.03 |
| Cyprid                |                 | Cirripedia                 | 12580        | 0.2116         | 0.2500 | 0.4616 | 686 | 15.38 | 8.55 | 23.93 |
| Fish (Traps)          |
| Postflexion           | Sparidae        | Diplodus capensis          | 6            | 1.5            | 1.5 | 3 | 7 | 1.0 | 0.4 | 1.4 |
|                       | Sparidae        | Rhabdosargus holubi        | 10           | 1.5            | 3.5 | 5 | 0 | 0 | 0 | 0 |
|                       | Dussumieriidae  | Etrumeus whiteheadi        | 55           | 22             | 5.5 | 27.5 | 290 | 53.7 | 2.9 | 56.6 |
|                       | Engraulidae     | Engraulis encrasicolus     | 1            | 0.5            | 0 | 0.5 | 177 | 34.4 | 0.2 | 34.6 |

This spreadsheet has merged cells, multiple rows as headers, and midway through it's got a new subheader "Fish (Traps)" where the student has separated out the fish species they recorded. The end result should look something like: 

| lifeStage | Family          | scientificName        | Class     | verbatimLocality | organismQuantity | organismQuantityType |
| --------- | --------------- | --------------------- | --------- | ---------------- | ---------------- | -------------------- |
| Zoea      | Pinnotheridae   | Pinnotheres sp.       | Crustacea | Jetty B          | 9.61521597       | % biomass            |
| Zoea      | Pinnotheridae   | Pinnixa sp.           | Crustacea | Jetty B          | 0.00961364       | % biomass            |
| Zoea      | Leucosiidae     |                       | Crustacea | Jetty B          | 0.00260522       | % biomass            |
| Megalopa  | Pinnotheridae   | Pinnotheres sp.       | Crustacea | Jetty B          | 0.03478523       | % biomass            |
| Megalopa  | Hymenosomatidae | Hymenosoma orbiculare | Crustacea | Jetty B          | 0.01368659       | % biomass            |
| Zoea      | Pinnotheridae   | Pinnotheres sp.       | Crustacea | Jetty D          | 84.3818376       | % biomass            |
| Zoea      | Pinnotheridae   | Pinnixa sp.           | Crustacea | Jetty D          | 0.03750053       | % biomass            |
| …         |                 |                       |           |                  |                  |                      |

So far GPT4o has not been able to achieve anything like this - it loses columns, hallucinates, mixes up and loses columns and rows. 

