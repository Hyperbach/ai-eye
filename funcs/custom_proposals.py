from funcs.builtins import type_inference_decorator


@type_inference_decorator()
def get_proposal_definition(proposal_style_name, structure_data, mapping_data):
    """
    Extracts and concatenates sections for a given proposal style name from mapping and structure data.

    Args:
    - proposal_style_name (str): The name of the proposal style to extract.
    - mapping_data (dict): The JSON data containing the mapping data.
    - structure_data (dict): The JSON data containing the structure data.

    Returns:
    - dict: A dictionary containing concatenated sections for the given proposal style.
    """
    style_data = None
    for style in mapping_data['proposal_styles']:
        if style['name'] == proposal_style_name:
            style_data = style
            break

    if not style_data:
        return {'error': 'Proposal style not found'}

    sections_info = {}
    for section, keys in style_data.items():
        if section != 'name' and section in structure_data:
            section_texts = []
            for key in keys:
                if key in structure_data[section]:
                    section_texts.append({
                        'key': key,
                        'description': structure_data[section][key].get('description', 'Description not found'),
                        'example': structure_data[section][key].get('example', 'Example not found')
                    })
            sections_info[section] = section_texts

    return sections_info
