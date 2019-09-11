import os
import re
import json
import tarfile
import distutils
from distutils import dir_util
import py_compile
import click

from pyfiglet import figlet_format
from PyInquirer import (Token, ValidationError, Validator, print_json, prompt, style_from_dict)

try:
    import colorama
    colorama.init()
except ImportError:
    colorama = None

try:
    from termcolor import colored
except ImportError:
    colored = None

IMPORTANT_FILES = {
    'connector_file': None,
    'connector_data': None,
    'metadata_file': None,
    'metadata_data': None,
    'replacerizer_file': None,
    'replacerizer_data': None,
    'dummy_data': []
}

IMPORTANT_SETTINGS = {
    'fail_on_data_not_found': None
}

PREAMBLE = '' \
        '{tab}{tab}#####################################\n' \
        '{tab}{tab}#### start DABCAT generated code ####\n' \
        '{tab}{tab}#####################################\n'

POSTAMBLE = '' \
        '{tab}{tab}#####################################\n' \
        '{tab}{tab}#### stop DABCAT generated code #####\n' \
        '{tab}{tab}#####################################\n'

style = style_from_dict({
    Token.QuestionMark: '#E91E63 bold',
    Token.Selected: '#673AB7 bold',
    Token.Instruction: '',  # default
    Token.Answer: '#2196f3 bold',
    Token.Question: '',
})

class file_validator(Validator):
    def validate(self, file_to_open):
        if len(file_to_open.text):
            try:
                with open(file_to_open.text, 'r') as opened_file:
                    return True
            except Exception as err:
                raise ValidationError(
                    message="File could not be found, or could not be opened. Details - {}".format(err.message),
                    cursor_position=len(file_to_open.text)
                )
        else:
            raise ValidationError(
                message="This field cannot be blank",
                cursor_position=len(file_to_open.text)
            )


def output(string, color, font="chunky", figlet=False):
    if colored:
        if not figlet:
            print(
                colored(string, color)
            )
        else:
            print(
                colored(
                    figlet_format(string, font=font),
                    color
                )
            )
    else:
        print(string)


def cat_banner():
    output('''                      /^--^\     /^--^\     /^--^\\
                      \____/     \____/     \____/
                     /      \   /      \   /      \\
                    |        | |        | |        |
                     \__  __/   \__  __/   \__  __/
|^|^|^|^|^|^|^|^|^|^|^|^\ \^|^|^|^/ /^|^|^|^|^\ \^|^|^|^|^|^|^|^|^|^|^|^|
| | | | | | | | | | | | |\ \| | |/ /| | | | | | \ \ | | | | | | | | | | |
########################/ /######\ \###########/ /#######################
| | | | | | | | | | | | \/| | | | \/| | | | | |\/ | | | | | | | | | | | |
|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|
''', "green")


def check_folder(directory='.', file_to_find=None, file_key=None):
    for root, dirs, files in os.walk(directory):
        for file_name in files:
            if file_to_find:
                if file_to_find.lower() == file_name.lower():
                    IMPORTANT_FILES[file_key] = '{}/{}'.format(directory, file_name)
                    return True
            else:
                if file_name.lower().endswith('_connector.py'):
                    IMPORTANT_FILES['connector_file'] = '{}/{}'.format(directory, file_name)
                elif 'replacerizer' in file_name.lower():
                    IMPORTANT_FILES['replacerizer_file'] = '{}/{}'.format(directory, file_name)
                elif '.json' in file_name.lower():
                    IMPORTANT_FILES['metadata_file'] = '{}/{}'.format(directory, file_name)
                
                if IMPORTANT_FILES['connector_file'] and IMPORTANT_FILES['metadata_file'] and IMPORTANT_FILES['replacerizer_file']:
                    return True
    
    if IMPORTANT_FILES['connector_file'] or IMPORTANT_FILES['metadata_file'] or IMPORTANT_FILES['replacerizer_file']:
        return True

    return False


def validate_known_data():
    output('Here\'s what we already know:', 'blue')
    
    if IMPORTANT_FILES['connector_file']:
        output('\tconnector file: {}'.format(IMPORTANT_FILES['connector_file']), 'cyan')
    if IMPORTANT_FILES['metadata_file']:
        output('\tmetadata file: {}'.format(IMPORTANT_FILES['metadata_file']), 'cyan')
    if IMPORTANT_FILES['replacerizer_file']:
        output('\treplacerizer File: {}'.format(IMPORTANT_FILES['replacerizer_file']), 'cyan')

    output('\n', 'grey')
    if not get_confirmation('is this correct?'):
        IMPORTANT_FILES['connector_file'] = None
        IMPORTANT_FILES['metadata_file'] = None
        IMPORTANT_FILES['replacerizer_file'] = None

    return


def read_important_files():
    file_keys = [key for key in IMPORTANT_FILES.keys() if '_file' in key and IMPORTANT_FILES[key]]
    for file_key in file_keys:
        with open(IMPORTANT_FILES[file_key], 'r') as important_file:
            file_data = important_file.read()
            
            if file_key in ['metadata_file', 'replacerizer_file']:
                file_data = json.loads(file_data)
            
            IMPORTANT_FILES[file_key.replace('_file', '_data')] = file_data

    return True


def process_data():
    processed_actions = []

    handle_action_re = re.compile(r'([ ]+def handle_action\([^)]+\)\:\n)')    
    handle_action_match = handle_action_re.search(IMPORTANT_FILES['connector_data'])
    tab = ' ' * (len(handle_action_match.groups()[0]) - len(handle_action_match.groups()[0].lstrip()))

    additional_imports = ''
    if 'import re' not in IMPORTANT_FILES['connector_data'].lower():
        additional_imports += 'import re\n'
    if 'import json' not in IMPORTANT_FILES['connector_data'].lower():
        additional_imports += 'import json\n'
    if 'from phantom.vault import vault' not in IMPORTANT_FILES['connector_data'].lower():
        additional_imports += 'from phantom.vault import Vault\n'
    if 'import uuid' not in IMPORTANT_FILES['connector_data'].lower():
        additional_imports += 'import uuid\n'
    if 'import tarfile' not in IMPORTANT_FILES['connector_data'].lower():
        additional_imports += 'import tarfile\n'

    connector_data_part_1 = IMPORTANT_FILES['connector_data'][0:handle_action_match.span()[1]]
    connector_data_part_2 = IMPORTANT_FILES['connector_data'][handle_action_match.span()[1]:]

    addition = PREAMBLE.format(tab=tab) \
        + '{tab}{tab}action = self.get_action_identifier()\n'.format(tab=tab)

    core_capability = \
        '{tab}{tab}dabcat_app_json = self.get_app_json()\n' \
        '{tab}{tab}dabcat_app_product = dabcat_app_json[\'product_name\']\n' \
        '{tab}{tab}dabcat_appid = dabcat_app_json[\'appid\']\n' \
        '{tab}{tab}def _dabcat_strip_artifact_identifiers(artifact_data):\n' \
        '{tab}{tab}{tab}artifact_data.pop(\'container_id\', None)\n' \
        '{tab}{tab}{tab}artifact_data.pop(\'container\', None)\n' \
        '{tab}{tab}{tab}artifact_data.pop(\'create_time\', None)\n' \
        '{tab}{tab}{tab}artifact_data.pop(\'start_time\', None)\n' \
        '{tab}{tab}{tab}artifact_data.pop(\'update_time\', None)\n' \
        '{tab}{tab}{tab}artifact_data.pop(\'id\', None)\n' \
        '{tab}{tab}{tab}artifact_data.pop(\'owner_id\', None)\n' \
        '{tab}{tab}{tab}artifact_data[\'ingest_app_id\'] = dabcat_appid\n' \
        '{tab}{tab}{tab}return artifact_data\n\n' \
        '{tab}{tab}def _dabcat_get_poll_vault_data(poll_vault_id, label):\n' \
        '{tab}{tab}{tab}poll_vault_id = poll_vault_id.strip()\n' \
        '{tab}{tab}{tab}poll_vault_path = Vault.get_file_path(poll_vault_id.strip())\n' \
        '{tab}{tab}{tab}poll_vault_info = Vault.get_file_info(vault_id=poll_vault_id.strip())\n' \
        '{tab}{tab}{tab}poll_vault_tmp_path = \'{{0}}/{{1}}\'.format(Vault.get_vault_tmp_dir(), poll_vault_info[0][\'name\'].replace(\'.tgz\',\'\'))\n' \
        '{tab}{tab}{tab}poll_vault_container_json = None\n' \
        '{tab}{tab}{tab}poll_vault_container_files = []\n' \
        '{tab}{tab}{tab}try:\n' \
        '{tab}{tab}{tab}{tab}with tarfile.open(poll_vault_path, \'r:gz\') as container_tar:\n' \
        '{tab}{tab}{tab}{tab}{tab}members = container_tar.getmembers()\n' \
        '{tab}{tab}{tab}{tab}{tab}for member in members:\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}member_file = container_tar.extractfile(member)\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}if not os.path.exists(poll_vault_tmp_path):\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}{tab}os.makedirs(poll_vault_tmp_path)\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}with open(\'{{0}}/{{1}}\'.format(poll_vault_tmp_path, os.path.basename(member_file.name)), \'w\') as container_file:\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}{tab}file_data = member_file.read()\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}{tab}container_file.write(file_data)\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}{tab}if os.path.basename(member_file.name).lower() == \'container.json\':\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}{tab}{tab}poll_vault_container_json = file_data\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}{tab}else:\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}{tab}{tab}poll_vault_container_files.append(os.path.basename(member_file.name))\n' \
        '{tab}{tab}{tab}except Exception as err:\n' \
        '{tab}{tab}{tab}{tab}_dabcat_early_failure(\'Unable to read poll data. Details - {{0}}\'.format(str(err)))\n' \
        '{tab}{tab}{tab}{tab}return False\n' \
        '{tab}{tab}{tab}poll_vault_container_data = json.loads(poll_vault_container_json)\n' \
        '{tab}{tab}{tab}for artifact in poll_vault_container_data[\'artifacts\']:\n' \
        '{tab}{tab}{tab}{tab}artifact = _dabcat_strip_artifact_identifiers(artifact)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'create_time\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'asset_id\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'due_time\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'id\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'hash\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'start_time\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'artifact_update_time\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'container_update_time\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'owner_id\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'label\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'current_phase_id\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'close_time\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'open_time\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'closing_owner_id\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'role_id\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'node_guid\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'in_case\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'owner_name\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'].pop(\'tenant_id\', None)\n' \
        '{tab}{tab}{tab}poll_vault_container_data[\'container\'][\'source_data_identifier\'] = str(uuid.uuid4())\n' \
        '{tab}{tab}{tab}container_details = poll_vault_container_data.pop(\'container\', None)\n' \
        '{tab}{tab}{tab}container_details[\'artifacts\'] = poll_vault_container_data.pop(\'artifacts\', None)\n' \
        '{tab}{tab}{tab}vault_documents = poll_vault_container_data.pop(\'vault_documents\', None)\n' \
        '{tab}{tab}{tab}container_details[\'label\'] = label\n' \
        '{tab}{tab}{tab}status, message, container_id = self.save_container(container_details)\n' \
        '{tab}{tab}{tab}try:\n' \
        '{tab}{tab}{tab}{tab}for poll_vault_container_file in poll_vault_container_files:\n' \
        '{tab}{tab}{tab}{tab}{tab}file_name = [vault_doc for vault_doc in vault_documents if vault_doc[\'hash\'] == poll_vault_container_file]\n' \
        '{tab}{tab}{tab}{tab}{tab}file_name = file_name[0][\'names\'][0] if file_name and file_name[0][\'names\'] else None\n' \
        '{tab}{tab}{tab}{tab}{tab}Vault.add_attachment(\'{{0}}/{{1}}\'.format(poll_vault_tmp_path, poll_vault_container_file), container_id, file_name=file_name)\n' \
        '{tab}{tab}{tab}except Exception as err:\n' \
        '{tab}{tab}{tab}{tab}_dabcat_early_failure(\'Unable to write poll data. Details - {{0}}\'.format(str(err)))\n' \
        '{tab}{tab}{tab}{tab}return False\n' \
        '{tab}{tab}{tab}return True\n\n' \
        '{tab}{tab}def _dabcat_add_other_artifacts(other_artifacts, replacerizer):\n' \
        '{tab}{tab}{tab}for other_artifact in other_artifacts:\n' \
        '{tab}{tab}{tab}{tab}if replacerizer:\n' \
        '{tab}{tab}{tab}{tab}{tab}other_artifact = json.dumps(other_artifact)\n' \
        '{tab}{tab}{tab}{tab}{tab}success, other_artifact = _dabcat_replacerize(other_artifact, replacerizer)\n' \
        '{tab}{tab}{tab}{tab}{tab}if not(success):\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}return False\n' \
        '{tab}{tab}{tab}{tab}{tab}other_artifact = json.loads(other_artifact)\n' \
        '{tab}{tab}{tab}{tab}if other_artifact[\'cef\'].get(\'vaultId\'):\n' \
        '{tab}{tab}{tab}{tab}{tab}vault_info = Vault.get_file_info(vault_id=other_artifact[\'cef\'][\'vaultId\'], container_id=other_artifact[\'container\'])\n' \
        '{tab}{tab}{tab}{tab}{tab}Vault.add_attachment(Vault.get_file_path(other_artifact[\'cef\'][\'vaultId\']), self.get_container_id(), file_name=vault_info[0][\'name\'])\n' \
        '{tab}{tab}{tab}{tab}other_artifact = _dabcat_strip_artifact_identifiers(other_artifact)\n' \
        '{tab}{tab}{tab}{tab}other_artifact[\'container_id\'] = self.get_container_id()\n' \
        '{tab}{tab}{tab}{tab}status, message, artifact_id = self.save_artifact(other_artifact)\n' \
        '{tab}{tab}{tab}{tab}if status == phantom.APP_ERROR:\n' \
        '{tab}{tab}{tab}{tab}{tab}_dabcat_early_failure(\'Could not load artifact. Details - {{0}}\'.format(message))\n' \
        '{tab}{tab}{tab}{tab}{tab}return False\n' \
        '{tab}{tab}{tab}{tab}\n' \
        '{tab}{tab}{tab}return True\n\n' \
        '{tab}{tab}def _dabcat_get_data(endpoint, params=None):\n' \
        '{tab}{tab}{tab}dabcat_base_url = self._get_phantom_base_url()\n' \
        '{tab}{tab}{tab}try:\n' \
        '{tab}{tab}{tab}{tab}r = requests.get(\'{{0}}rest/{{1}}\'.format(dabcat_base_url, endpoint), params=params, verify=False)\n' \
        '{tab}{tab}{tab}except Exception as e:\n' \
        '{tab}{tab}{tab}{tab}message = (\'Action run failed. Exception: {{0}}\').format(e.message)\n' \
        '{tab}{tab}{tab}{tab}return False, message\n' \
        '{tab}{tab}{tab}if r is None:\n' \
        '{tab}{tab}{tab}{tab}return False, \'Unable to retrieve configuration data\'\n' \
        '{tab}{tab}{tab}return True, r.json()\n\n' \
        '{tab}{tab}def _dabcat_early_failure(message):\n' \
        '{tab}{tab}{tab}action_result = self.add_action_result(ActionResult(dict(param)))\n' \
        '{tab}{tab}{tab}action_result.set_status(phantom.APP_ERROR, message)\n' \
        '{tab}{tab}{tab}return action_result.get_status()\n\n' \
        '{tab}{tab}def _dabcat_get_vault_data(vault_id):\n' \
        '{tab}{tab}{tab}vault_data = None\n' \
        '{tab}{tab}{tab}try:\n' \
        '{tab}{tab}{tab}{tab}vault_path = Vault.get_file_path(vault_id)\n' \
        '{tab}{tab}{tab}{tab}with open(vault_path, \'r\') as vault_file:\n' \
        '{tab}{tab}{tab}{tab}{tab}vault_data = vault_file.read()\n' \
        '{tab}{tab}{tab}except Exception as err:\n' \
        '{tab}{tab}{tab}{tab}_dabcat_early_failure(\'Could not retrieve data. Details - {{0}}\'.format(str(err)))\n' \
        '{tab}{tab}{tab}{tab}return False, None\n' \
        '{tab}{tab}{tab}return True, vault_data\n\n' \
        '{tab}{tab}def _dabcat_replacerize(action_result_data, vault_id):\n' \
        '{tab}{tab}{tab}success, replacerizer_json = _dabcat_get_vault_data(vault_id)\n' \
        '{tab}{tab}{tab}if not(success):\n' \
        '{tab}{tab}{tab}{tab}return False, None\n' \
        '{tab}{tab}{tab}replacerizer_json = json.loads(replacerizer_json)\n' \
        '{tab}{tab}{tab}for replace_value in replacerizer_json.keys():\n' \
        '{tab}{tab}{tab}{tab}action_result_data = action_result_data.replace(replace_value, replacerizer_json[replace_value])\n' \
        '{tab}{tab}{tab}replacerizer_wholesale = r\'(?:\\*\\*\\*)([^\\*]+)(?:\\*\\*\\*)\'\n' \
        '{tab}{tab}{tab}action_result_data = re.sub(replacerizer_wholesale, lambda x: param[x.group().replace(\'*\',\'\')], action_result_data)\n' \
        '{tab}{tab}{tab}return True, action_result_data\n\n' \
        '{tab}{tab}params = {{\'_filter_label\': \'"demo_configuration"\', \'_filter_name\': \'"{{0}}"\'.format(dabcat_app_product), \'_filter_description__icontains\': \'"{{0}}"\'.format(action)}}\n' \
        '{tab}{tab}success, demo_config_container = _dabcat_get_data(\'container\', params=params)\n' \
        '{tab}{tab}if (not(success) or demo_config_container[\'count\']) == 0 and {fail_option} == True:\n' \
        '{tab}{tab}{tab}return _dabcat_early_failure(\'There is no data for the action/parameter selected\')\n' \
        '{tab}{tab}elif success:\n' \
        '{tab}{tab}{tab}matching_artifact = None\n' \
        '{tab}{tab}{tab}default_artifact = None\n' \
        '{tab}{tab}{tab}other_artifacts = []\n' \
        '{tab}{tab}{tab}poll_artifacts = []\n' \
        '{tab}{tab}{tab}default_other_artifacts = []\n' \
        '{tab}{tab}{tab}is_default = False\n' \
        '{tab}{tab}{tab}for datum in demo_config_container[\'data\']:\n' \
        '{tab}{tab}{tab}{tab}artifact_params = {{\'_filter_container_id\': datum[\'id\']}}\n' \
        '{tab}{tab}{tab}{tab}artifact_success, demo_config_artifacts = _dabcat_get_data(\'artifact\', params=artifact_params)\n' \
        '{tab}{tab}{tab}{tab}if not artifact_success:\n' \
        '{tab}{tab}{tab}{tab}{tab}return _dabcat_early_failure(\'Unable to retrieve action data. Details: {{0}}\'.format(str(demo_config_artifact)))\n' \
        '{tab}{tab}{tab}{tab}param_matches = [False]\n' \
        '{tab}{tab}{tab}{tab}for artifact in demo_config_artifacts[\'data\']:\n' \
        '{tab}{tab}{tab}{tab}{tab}if action == \'on_poll\' and artifact[\'name\'].lower().replace(\' \', \'_\') == \'poll_artifact\':\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}poll_artifacts.append(artifact)\n' \
        '{tab}{tab}{tab}{tab}{tab}elif artifact[\'name\'].lower().replace(\' \',\'_\') == \'matching_criteria\':\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}if not(artifact[\'cef\'].get(\'dummy_default\')):\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}{tab}matching_artifact = artifact\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}else:\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}{tab}default_artifact = artifact\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}{tab}is_default = True\n' \
        '{tab}{tab}{tab}{tab}{tab}else:\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}other_artifacts.append(artifact)\n' \
        '{tab}{tab}{tab}{tab}if matching_artifact:\n' \
        '{tab}{tab}{tab}{tab}{tab}param_matches = [param.get(cef_key) == matching_artifact[\'cef\'][cef_key] for cef_key in matching_artifact[\'cef\'].keys() if cef_key != \'replacerizer\' and cef_key != \'dummy_file_vault_id\']\n' \
        '{tab}{tab}{tab}{tab}{tab}if all(param_matches):\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}break\n' \
        '{tab}{tab}{tab}{tab}{tab}else:\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}matching_artifact = None\n' \
        '{tab}{tab}{tab}{tab}if is_default:\n' \
        '{tab}{tab}{tab}{tab}{tab}default_other_artifacts = other_artifacts\n' \
        '{tab}{tab}{tab}{tab}is_default = False\n' \
        '{tab}{tab}{tab}if action == \'on_poll\':\n' \
        '{tab}{tab}{tab}{tab}if not(poll_artifacts) and {fail_option} == True:\n' \
        '{tab}{tab}{tab}{tab}{tab}return _dabcat_early_failure(\'Theres is no data for polling action\')\n' \
		'{tab}{tab}{tab}{tab}elif poll_artifacts:\n' \
		'{tab}{tab}{tab}{tab}{tab}action_result = self.add_action_result(ActionResult(dict(param)))\n' \
		'{tab}{tab}{tab}{tab}{tab}for poll_artifact in poll_artifacts:\n' \
		'{tab}{tab}{tab}{tab}{tab}{tab}success = _dabcat_get_poll_vault_data(poll_artifact[\'cef\'][\'vaultId\'], poll_artifact[\'cef\'][\'label\'])\n' \
		'{tab}{tab}{tab}{tab}{tab}{tab}if not(success):\n' \
		'{tab}{tab}{tab}{tab}{tab}{tab}{tab}return action_result.get_status()\n' \
		'{tab}{tab}{tab}{tab}{tab}return action_result.set_status(phantom.APP_SUCCESS, \'Poll successful\')\n' \
        '{tab}{tab}{tab}else:\n' \
        '{tab}{tab}{tab}{tab}data_artifact = matching_artifact if matching_artifact else default_artifact\n' \
        '{tab}{tab}{tab}{tab}if not(data_artifact) and {fail_option} == True:\n' \
        '{tab}{tab}{tab}{tab}{tab}return _dabcat_early_failure(\'There is no data for the action/parameter selected\')\n' \
        '{tab}{tab}{tab}{tab}elif data_artifact:\n' \
        '{tab}{tab}{tab}{tab}{tab}other_artifacts = other_artifacts if matching_artifact else default_other_artifacts\n' \
        '{tab}{tab}{tab}{tab}{tab}action_result_data = None\n' \
        '{tab}{tab}{tab}{tab}{tab}try:\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}vault_success, action_result_data = _dabcat_get_vault_data(data_artifact[\'cef\'].get(\'dummy_file_vault_id\',\'\').strip())\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}vault_path = Vault.get_file_path(data_artifact[\'cef\'].get(\'dummy_file_vault_id\',\'\').strip())\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}with open(vault_path, \'r\') as vault_file:\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}{tab}action_result_data = vault_file.read()\n' \
        '{tab}{tab}{tab}{tab}{tab}except Exception as err:\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}return _dabcat_early_failure(\'Unable to retrieve data. Details - {{0}}\'.format(str(err)))\n' \
        '{tab}{tab}{tab}{tab}{tab}action_result = self.add_action_result(ActionResult(dict(param)))\n' \
        '{tab}{tab}{tab}{tab}{tab}if data_artifact[\'cef\'].get(\'replacerizer\'):\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}success, action_result_data = _dabcat_replacerize(action_result_data, data_artifact[\'cef\'].get(\'replacerizer\'))\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}if not(success):\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}{tab}return action_result.get_status()\n' \
        '{tab}{tab}{tab}{tab}{tab}try:\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}action_result_data = json.loads(action_result_data)\n' \
        '{tab}{tab}{tab}{tab}{tab}except Exception as err:\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}return _dabcat_early_failure(\'Unable to load data. Details - {{0}}\'.format(str(err)))\n' \
        '{tab}{tab}{tab}{tab}{tab}action_result.update_summary(action_result_data[0][\'summary\'])\n' \
        '{tab}{tab}{tab}{tab}{tab}for data_result in action_result_data:\n' \
        '{tab}{tab}{tab}{tab}{tab}{tab}action_result.add_data(data_result[\'data\'])\n' \
        '{tab}{tab}{tab}{tab}{tab}return action_result.set_status(phantom.APP_SUCCESS, \'{{0}}\'.format(action_result_data[0][\'message\']))\n'.format(
            tab=tab, fail_option=IMPORTANT_SETTINGS['fail_on_data_not_found']
        )

    addition = '{addition}{core_capability}{postamble}'.format(addition=addition, core_capability=core_capability, postamble=POSTAMBLE.format(tab=tab))

    final_data = '{additional_imports}{part_1}{addition}{part_2}'.format(
        additional_imports=additional_imports,
        part_1=connector_data_part_1,
        addition=addition,
        part_2=connector_data_part_2
    )

    IMPORTANT_FILES['connector_data'] = final_data
    
    return


def collect_settings():
    questions = [
        {
            'type': 'input',
            'name': 'app_name',
            'message': 'what do you want to call this app (do not use the same name as the existing production app name) ex: {}?'.format(
                '{} DEV'.format(IMPORTANT_FILES['metadata_data']['name'])
            ),
            'validate': lambda val: (val or '') != '' or 'a name must be provided'
        },
        {
            'type': 'input',
            'name': 'product_name',
            'message': 'what do you want to call this product (do not use the same name as the existing production product name) ex: {}?'.format(
                '{} DEV'.format(IMPORTANT_FILES['metadata_data']['product_name'])
            ),
            'validate': lambda val: (val or '') != '' or 'a product name must be provided'
        },
        {
            'type': 'input',
            'name': 'app_id',
            'message': 'what do you want to use for the app_id (do not use the same app_id as the existing production app)?',
            'validate': lambda val: (val or '') != '' or 'an app id must be provided'
        },
        {
            'type': 'confirm',
            'name': 'fail_option',
            'message': 'do you want the app to fail if no matching action/parameter combinations and no default action results are found?'
        }
    ]

    answers = prompt(questions)

    IMPORTANT_FILES['metadata_data']['name'] = answers['app_name']
    IMPORTANT_FILES['metadata_data']['product_name'] = answers['product_name']
    IMPORTANT_FILES['metadata_data']['appid'] = answers['app_id']
    IMPORTANT_SETTINGS['fail_on_data_not_found'] = answers['fail_option']

    return


def verify():
    output('Here\'s a review', 'blue')
    output('\tdummy app name: {}'.format(IMPORTANT_FILES['metadata_data']['name']), 'cyan')
    output('\tdummy app product name: {}'.format(IMPORTANT_FILES['metadata_data']['product_name']), 'cyan')
    output('\tdummy app appid: {}'.format(IMPORTANT_FILES['metadata_data']['appid']), 'cyan')
    
    questions = [{
        'type': 'confirm',
        'name': 'are_you_sure',
        'message': 'yes, i know that\'s not everyting... but do you feel confident that this is all correct?'
    }]
    
    answer = prompt(questions)

    return answer['are_you_sure']


def create_files():

    new_name = '{}_{}'.format(
        IMPORTANT_FILES['metadata_data']['name'].lower().replace(' ', '_'),
        'dummy'
    )

    cwd = os.getcwd()
    new_dir = '{}/{}'.format(cwd[:cwd.rfind('/')], new_name)

    distutils.dir_util.copy_tree('.', new_dir)

    with open('{}/{}'.format(new_dir, IMPORTANT_FILES['connector_file']), 'w+') as connector_file:
        connector_file.write(IMPORTANT_FILES['connector_data'])

    with open('{}/{}'.format(new_dir, IMPORTANT_FILES['metadata_file']), 'w+') as metadata_file:
        metadata_file.write(json.dumps(IMPORTANT_FILES['metadata_data'], indent=4))

    for root, dirs, files in os.walk(new_dir):
        for file_name in files:
            if file_name.endswith('.py'):
                py_compile.compile('{}/{}'.format(new_dir, file_name))
    
    with tarfile.open('{}/{}.tgz'.format(cwd[:cwd.rfind('/')], new_name), mode='w:gz') as dummy_tar:
        dummy_tar.add(new_dir, arcname=new_name)

    output('congratulations! you\'re done - go try out your shiny new app', 'blue')
    output('\t{}/{}.tgz'.format(cwd[:cwd.rfind('/')], new_name), 'cyan')
    output('\t{} <- source files here'.format(new_dir), 'cyan')
    return


def read_dummy_data(file_name):
    dummy_data = None

    with open(file_name, 'r') as dummy_file:
        dummy_data = dummy_file.read()
        if IMPORTANT_FILES['replacerizer_file']:
            dummy_data = replacerize(dummy_data)
        dummy_data = json.loads(dummy_data)
        if dummy_data[0].get('data') is None and dummy_data[0].get('summary') is None:
            raise Exception('critical fields missing from dummy data - must include keys "data" and "summary"')
        
    return dummy_data


def replacerize(file_data):
    for replace_value in IMPORTANT_FILES['replacerizer_data'].keys():
        file_data = file_data.replace(replace_value, IMPORTANT_FILES['replacerizer_data'][replace_value])

    return file_data


def get_confirmation(message):
    question = [
        {
            'type': 'confirm',
            'name': 'confirmed',
            'message': message
        }
    ]

    answer = prompt(question)

    return answer['confirmed']


@click.command()
def main():
    
    cat_banner()
    output('DABCAT2.0', 'green', figlet=True)
    output('Dummy App Builder for Code And Transforms (Now Improved with Version 2.0)\n\n', 'green')
    
    any_known = check_folder()
    if any_known:
        validate_known_data()
    else:
        output('it appears something went wrong. are you sure you started DABCAT2.0 from the app code directory? Please try again', 'red')

    try:
        read_important_files()
    except Exception as err:
        output('unable to process files, exiting DABCAT; details - {}'.format(str(err)), 'red')

    collect_settings()
    process_data()
    
    if not(verify()):
        output('i\'m so sorry this didn\'t work out - please come back and try again later', 'red')
        return
    create_files()


if __name__ == '__main__':
    main()