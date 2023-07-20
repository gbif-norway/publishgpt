import re

main_agent = """The user has uploaded {dataframes_no} dataframe(s) - (df_ids = {dataframe_ids}). The plan is to publish these with the {core} DwC core, and {extensions} DwC extension(s).
    In order to achieve this aim, you have to run through the following tasks:
    {plan}
    Do as much work as possible on preparing the data for publication, but ask for clarification from the user if you are unsure of anything.
    Strategically check-in with users (e.g. showing snapshots of data) at certain points, and make sure they are happy with your progress.
    """


get_next_task = """
    Current data state:
    ---
    {df_samples}
    ---
    Overall plan and progress:
    {plan}
    ---
    generate next task somehow... ?
    """

get_main_dataframe = """
    Carefully examine these dataframe samples, paying attention to the shape, description and problems that have been identified. 
    ---
    {df_samples}
    ---
    Decide on a suitable Darwin Core, one of: Taxon core, Occurrence core, Event core, or Simple Darwin Core (Event core with Occurrences combined).
    """


agent_system_message = """
    You are a friendly, helpful agent (agent_id {agent_id}) in a chatbot system, helping a user prepare their dataset (dataset_id {dataset_id}) for publication on gbif.org. 
    Note: users are field biologists and ecologists with no knowledge of data standards or how to structure data, so when interacting with the user explain technical terms and concepts simply.
    {body}
    Once you and the user are happy with the result, set your task to complete using SetTaskToComplete with agent_id = {agent_id}
"""

extract_subtables = """
    A user has uploaded a spreadsheet, which has been converted into a pandas dataframe with dtype='str', header=None. The dataframe is stored in the `df` field of a Django model called DatasetFrame, which is associated with a Dataset model:
    class Dataset(models.Model):
        created = models.DateTimeField(auto_now_add=True)
    class DatasetFrame(models.Model):
        created = models.DateTimeField(auto_now_add=True)
        dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
        title = models.CharField(max_length=200, blank=True)
        df = PickledObjectField()  # Contains dataframe
        parent = models.ForeignKey('DatasetFrame', on_delete=models.CASCADE, blank=True, null=True)
    
    Currently, you are working with DatasetFrame id {df_id}. Here's a snapshot of it:
    {snapshot}
    Your task is to separate out any sub tables in this dataframe into new, separate DatasetFrames. New DatasetFrames should have the parent set to {df_id}, and should also stay associated with the same dataset (id = {ds_id}).
    """

explain_extracted_subtables = """
    I have just had a quick look at your spreadsheet "{title}". Based on the empty rows & columns which appear to be acting as "dividers" between the sub-tables, I think it contains {len} different, separate tables:
    {snapshots}
    Is this correct? Please let me know: a) if there are any separate sub-tables I missed which should be split off, and b) if there are any sub-tables that should be joined to other sub-tables. An important step in publishing your data is getting every table loaded separately. 
"""

# # I think best is to let it spawn new Agents 
# it needs to have a set list of tasks it works through
# or should it have just a state it needs to get to before it can proceed to the next task? taht seems more promising 

# maybe should just mark old dataframes as 'stale' when it makes a new one? or set a date archived_on

