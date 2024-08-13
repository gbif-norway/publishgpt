# Welcome to ChatIPT ![logosmall](https://github.com/user-attachments/assets/9aded457-b39e-41dc-bad6-92a9258ac563)



ChatIPT is a chatbot for students and researchers who are new to data publication or only occasionally publish data.

It cleans and standardises spreadsheets, creates basic metadata, asking the user for guidance where necessary through natural conversation. Finally, it publishes the data on gbif.org as a Darwin Core Archive.

* * *

**Why is it necessary?**

At a conservative estimate, there are 300 - 400 PhDs and MScs in Europe alone at the moment generating biodiversity data, as well as countless small biodiversity research studies.

Publishing piecemeal but high quality data such as this is difficult to do at scale:

*   🤔 Data standardisation is hard and requires specialist knowledge of:
    *   data standards and the the domain of standardisation (e.g. ontologies, etc)
    *   programming languages (e.g. R, Python, SQL)
    *   data management techniques (e.g. normalisation, wide vs long format, etc)
    *   familiarity with specialised software (e.g. OpenRefine and the IPT, etc)
*   📨 No open access to publishing facilities - users have to know who to email and have to wait to get added to IPTs manually
*   🕐 GBIF node staff time and resources are limited
*   🧑‍🎓 Training workshops can help, but:
    *   are costly and time consuming
    *   teach generic techniques which users find difficult to put into practice in the real world
    *   have logistical and language barriers
    *   have to be done regularly: users who only publish data once or twice a year forget how to do it and need the same help every time

ChatIPT solves these problems: a non-technical user without training or specialist knowledge only needs a web browser and verified ORCID account to go from an unformatted, raw spreadsheet to standardised, published data on GBIF.

* * *

**Future plans**

1.  Restrict access with an ORCID login
2.  Build in strict safety rails to ensure the bot is only used for legitimate data publication
3.  Create a front page dashboard listing a logged-in user's datasets, along with some stats for each dataset from the GBIF API
4.  Provide edit access for already published or work-in-progress datasets
5.  Currently publishing using the GBIF Norway publishing institution - this would need to be opened up to more countries. National nodes would sign up for it (agreeing that ad-hoc users can publish to a generic national institution), and publicise it at their higher education institutions.
6.  Only works well at the moment for occurrence data - expand to sampling event, checklist and others.
7.  Add support for frictionless data & the new data models
8.  Test chatbot thoroughly in other languages
9.  Parse PDF uploads (e.g. drafts of journal papers) to create better metadata for each dataset
10.  Use the details from the user's ORCID login to give chatbot context so it can provide more tailored help. For example, it could read biographies to discover user's area of expertise and make inferences about the data from that, automatically get current institution name + address for metadata, work out likely level of experience with data publication and tailor language accordingly, and more. The chatbot could also be more personalised and human-like, addressing the user by name, commenting on the new dataset compared to the old work done previously, etc.
11.  Currently using OpenAI's gpt4o model - experiment with open source models to reduce costs, depending on uptake
* * *
Note: Not suitable for publishing data from a database, or for large data sources, and there are no plans to support this. A chatbot is not the right format as it needs to be done by a technician who understands the database, and as there are far fewer databases than ad-hoc spreadsheets it is (in many ways) a different problem, which we already have a great tool for: the IPT. The IPT is less good for those new to data publication who only need to publish a small, single datase once or twice every few years.
