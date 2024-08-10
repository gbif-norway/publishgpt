import yaml
import re

def parse_document(file_path):
    # Read the file content
    with open(file_path, 'r') as file:
        content = file.read()

    # Split the content by sections
    sections = content.split('## ')
    sections_dict = {}

    for section in sections:
        if section.strip():
            # Extract the section heading and content
            lines = section.splitlines()
            section_heading = lines[0].strip()
            section_content = "\n".join(lines[1:])
            sections_dict[section_heading] = section_content

    return sections_dict

def extract_terms_from_section(section_content):
    # Use regex to extract relevant parts of the section
    tables = re.findall(r'<table class="table">.*?<tbody>.*?</tbody>\n</table>', section_content, re.DOTALL)
    terms = {}

    for table in tables:
        term_name_match = re.search(r'<tr class="table-secondary"><th colspan="2">(.*?)</th></tr>', table)
        if term_name_match:
            term_name = term_name_match.group(1).strip()
            definition_match = re.search(r'<tr><td>Definition</td><td>(.*?)</td></tr>', table, re.DOTALL)
            examples_match = re.search(r'<tr><td>Examples</td><td>(.*?)</td></tr>', table, re.DOTALL)
            
            definition = re.sub(r'<.*?>', '', definition_match.group(1).strip()) if definition_match else ""
            examples = re.findall(r'<li class="list-group-item"><code>(.*?)</code></li>', examples_match.group(1)) if examples_match else []
            examples_text = ' / '.join(examples)

            terms[term_name] = {
                "definition": definition,
                "examples": examples_text
            }

    return terms

def format_terms(terms_data):
    formatted_output = ""
    exclude = ['license', 'rightsHolder', 'accessRights', 'bibliographicCitation', 'datasetID', 'datasetName', 'dataGeneralizations']
    for section, terms in terms_data.items():
        if term in exclude:
            continue
        formatted_output += f"{section}:\n"
        for term, details in terms.items():
            formatted_output += f"  {term}: {details['definition']}"
            if details['examples']:
                formatted_output += f" Egs - {details['examples']}\n"
            else:
                formatted_output += "\n"
    return formatted_output

def parse_and_format_terms(file_path):
    sections_dict = parse_document(file_path)
    parsed_terms = {}

    for section_heading, section_content in sections_dict.items():
        if section_heading in ["Record-level", "Occurrence", "Organism", "MaterialEntity", 
                               "MaterialSample", "Event", "Location", "GeologicalContext", "Identification", "Taxon", "MeasurementOrFact"]:
            parsed_terms[section_heading] = extract_terms_from_section(section_content)
    
    return format_terms(parsed_terms)

# From https://github.com/tdwg/dwc/blob/master/docs/terms/index.md
input_file_path = 'api/templates/dwc-quick-reference-guide.md.txt'
output_file_path = 'api/templates/dwc-quick-reference-guide.yaml'

# Read the markdown file
# with open(input_file_path, 'r', encoding='utf-8') as file:
#     content = file.read()

parsed_and_formatted_output = parse_and_format_terms(input_file_path)

# Save the results to a YAML file
with open(output_file_path, 'w', encoding='utf-8') as text_file:
    text_file.write(parsed_and_formatted_output)
