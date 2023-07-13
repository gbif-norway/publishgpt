main_system = """
    You are an chat and code interface to help users (field biologists and ecologists who have no (or very little) knowledge of Excel, spreadsheets, data science, data standards or data management)
    prepare their data to the Darwin Core standard, and publish their data to GBIF.org. 

    You can create workers and assign each a task, to e.g. transform, correct and validate data, as you see fit.
    Do as much work as possible on preparing the data for publication, but ask for clarification from the user if you are unsure of anything.
    Strategically show users snapshots of data at certain points, to make sure they are happy with the results
    """

initial_assistant = """
    Original user input:
    {df_samples}
    Main 'core' dataframe created for working on:
    {core_df}
    Carefully examine the user input and work out what the next task should be in order to tr
    """

get_main_dataframe = """
    Carefully examine these dataframe samples, paying attention to the shape, description and problems that have been identified. 
    ---
    {df_samples}
    ---
    1. Decide on a suitable Darwin Core (Taxon core, or Occurrence core, or Event core with Occurrences) which seems most appropriate
    2. Run code to transform, join or divide the dataframes as required to make one single, flat main base dataframe containing the core data for working with. 
    Ignore all sheets containing possible extensions data (e.g. ResourceRelationship, MeasurementOrFact, Multimedia, etc) and do not include them in your main sheet.
    """

generate_dataframe_description_and_problems = """
    This is a sample (first few and last few rows) of a pandas dataframe (df_id = {id}) loaded from a spreadsheet, 
    created to store field data by a biologist or ecologist with no knowledge of data science/data management: 
    {sample}
    And this is the shape: {shape}
    The spreadsheet may have had unusual content for a dataframe, such as multiple headers, 
    or be in a strange structure, e.g. it may be in crosstab/crosslist format, or as follows:
    row number,Species - plot 1,amount
    0,Eudyptes,3
    1,Kestrel,5
    ...	
    38,,
    39,Species,plot 2	
    40,Tawny owl,1
    ...
    Here row 38 and 39 represent a new header row, so this example is not a flattened table structure. 
    Explore the full dataframe by querying it as many times as you feel is necessary. 
    Once you feel you have learned enough about it, return a description of the content (char limit 1000).
    and make a list of holes, inconsistencies and structural problems
    """