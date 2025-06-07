import json
import os
import re
import chardet
import subprocess
import uuid
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
from atlassian import Confluence
import requests
from bs4 import NavigableString
from dotenv import load_dotenv
import binascii
from Crypto.Hash import SHA256, HMAC

load_dotenv()
images_folder = "images"
space_key=os.getenv("space_key")
shared_paragraph_space_key=os.getenv("shared_paragraph_space_key")

#credentials for authentication
BASE_URL = "https://rest.opt.knoiq.co/api/v1"
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
SITE_ID = os.getenv("SITE_ID") 
USER_TYPE = "Admin" 
SECRET_KEY = os.getenv("SECRET_KEY")

#knosys authentication
def get_auth_challenge():
    try:
        url = f"{BASE_URL}/auth/challenge"
        payload = {
            "accessToken": ACCESS_TOKEN,
            "siteId": SITE_ID,
            "userType": USER_TYPE
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers, verify=False)
        if response.status_code == 200:
            challenge_token = response.json().get("challengeString")
            return challenge_token
        else:
            print("[:x:] Failed to get challenge:", response.text)
            return None
    except Exception as E:
        print(E)
        
def generate_signature(challenge_token):
    try:
        hex_bytes = bytes.fromhex(SECRET_KEY)
        secret_b64 = binascii.b2a_base64(hex_bytes).decode("utf-8").strip()
        secret_key_encoded = binascii.a2b_base64(secret_b64)
        hash_value = HMAC.new(secret_key_encoded, challenge_token.encode("utf-8"), digestmod=SHA256)
        signature = binascii.b2a_base64(hash_value.digest()).decode("utf-8").strip()
        return signature
    except Exception as E:
        print(E)

def get_auth_token(challenge_token, signature):
    try:
        url = f"{BASE_URL}/auth/token"
        payload = {
            "challenge": challenge_token,
            "signature": signature
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers, verify=False)
        if response.status_code == 200:
            auth_token = response.json().get("token")
            print("[:white_tick:] Authentication successful! Token received.")
            return auth_token
    
        else:
            print("[:x:] Authentication failed:", response.text)
            return None
    except Exception as e:
        print(e)
    
challenge = get_auth_challenge()
if challenge:
    signature = generate_signature(challenge)
    auth_token = get_auth_token(challenge, signature)
    
Document_Id=""
confluence_email =" "

#knosys credentials
source_url=os.getenv("source_url")
headers_1={"Content-Type":"application/json", "Authorization":f"Bearer {auth_token}"}

#get author email from knosys
def getuserEmail(created_by):
    with open("users.json", "r") as f:
        email_map = json.load(f)
    def get_confluence_email(kiq_email):
        return email_map.get(kiq_email, "Not found")
    return get_confluence_email(created_by)

#fetch_documents
response=requests.get(source_url,headers=headers_1)
if response.status_code == 200:
    try:
        data = response.json()
        fields = data.get("fields", []) 
        Document_Id = data['detail']['id']
        Created_by=data['detail']['createdByPerson']
        confluence_email=getuserEmail(Created_by)
        title = data['detail']['title']
        print("Document Title:", title)
    except ValueError:
        print("Failed to parse JSON.")
else:
    print(f"Request failed with status code: {response.status_code}")

#confluence_credentials   
api_token=os.getenv("CONFLUENCE_API_TOKEN")
confluence_url =os.getenv("CONFLUENCE_URL")
auth = HTTPBasicAuth(confluence_email, api_token)
headers={"Content-Type": "application/json"}

def get_page_by_title(space_key, title):
    try:
        url = f"{confluence_url}/content"
        params = {
            "spaceKey": space_key,
            "title": title,
            "expand": "version"
        }
        response = requests.get(url, headers=headers, auth=auth, params=params)
        if response.status_code == 200 and response.json()["size"] > 0:
            # print(response.status_code,"-->",response.text)
            print("Page Title fetched!")
            return response.json()["results"][0]
        else:
            print(response.status_code,"-->",response.text)
    except Exception as E:
        print(E)

def get_current_version(page_id):
    url = f"{confluence_url}/content/{page_id}?expand=version"
    resp = requests.get(url, headers=headers, auth=auth)
    if resp.status_code == 200:
        return resp.json()['version']['number']
    else:
        print(f"Failed to get page version: {resp.status_code} - {resp.text}")
        return None
    
def create_page(space_key, title, content):
    url = f"{confluence_url}/content"
    print(url,space_key, title, content)
    data = {
        "version": {
        "number": 1
        },
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {
            "storage": {
                "value": content,
                "representation": "storage"
            }
        }
    }
    try:
        response = requests.post(url, headers=headers, auth=auth, data=json.dumps(data))
        if(response.status_code==200):
            response_json = response.json()
            # print(response.status_code,"-->",response.text)
            print("page created")
            created_page_Id=response_json.get("id")
            return created_page_Id
        else:
            print(response.status_code,"-->",response.text)
    except Exception as e:
        print(e)

def attach_file(page_id, file_path, file_name):
    if file_name == "2e6d82ef-524c-ea11-a960-000d3ad095fb.png":
        print(f"Skipped upload for unwanted image: {file_name}")
        return None
    upload_url = f"{confluence_url}/content/{page_id}/child/attachment"
    
    headers_no_json = {
        "X-Atlassian-Token": "no-check",  # prevents XSRF check
        "Accept": "application/json"
    }
    with open(file_path, "rb") as f:
        files = {
            'file': (file_name, f, 'image/png')
        }
        response = requests.post(upload_url, headers=headers_no_json, auth=auth, files=files)
    try:
        if response.status_code == 200 or response.status_code == 201:
            print(f"Uploaded: {file_name}")
            return response.json()
        else:
            print(f"Failed to upload {file_name}: {response.status_code} - {response.text}")
            return None
    except Exception as E:
        print(e)

def update_page(page_id, title, html_content, current_version):
    try:
        url = f"{confluence_url}/content/{page_id}"
        data = {
            "id": page_id,
            "type": "page",
            "title": title,
            "version": {"number": current_version + 1},
            "body": {
                "storage": {
                    "value": html_content,
                    "representation": "storage"
                }
            }
        }
        response = requests.put(url, headers=headers, auth=auth, data=json.dumps(data))
        print(response.status_code)
        if(response.status_code == 200):
            # print(response.status_code,"-->",response.text)
            print("page updated")
        else:
            print(response.status_code,"-->",response.text)
        return None
    except Exception as E:
        print(E)
        
external_info_list = data.get("external", {}).get("information", [])
info_lookup = {item["informationId"]: item for item in external_info_list if "informationId" in item}

def generate_image_macro_img(filename):
    if filename == "2e6d82ef-524c-ea11-a960-000d3ad095fb.png":
        print(f"Skipped macro generation for: {filename}")
        return " "
    return f'''
<ac:image>
  <ri:attachment ri:filename="{filename}"/>
</ac:image>
'''.strip()

def get_tooltip_panel_content(external_id):
    try:
        entry = info_lookup.get(external_id)
        if not entry:
            return None
        info_type = entry.get("informationType")
        content = entry.get("content", "")

        def fetch_and_save_image(item_id):
            url = f'https://rest.opt.knoiq.co/api/v2/resources/images/{item_id}'
            response = requests.get(url, headers=headers_1)

            if response.status_code == 200:
                os.makedirs(images_folder, exist_ok=True)
                filepath = os.path.join(images_folder, f"{item_id}.png")
                with open(filepath, "wb") as f:
                    f.write(response.content)
                return filepath
            else:
                return None

        if info_type == "Image / screenshot":
            soup = BeautifulSoup(content, "html.parser")
            img_tag = soup.find("img")
            if img_tag and img_tag.get("itemid"):
                item_id = img_tag["itemid"]
                filepath = fetch_and_save_image(item_id)
                if filepath:
                    return generate_image_macro_img(os.path.basename(filepath))
            return None

        if info_type is None or info_type == "HTML":
            soup = BeautifulSoup(content, "html.parser")
            img_tags = soup.find_all("img")
            for img_tag in img_tags:
                item_id = img_tag.get("itemid")
                if item_id:
                    filepath = fetch_and_save_image(item_id)
                    if filepath:
                        return generate_image_macro_img(os.path.basename(filepath))

            title = entry.get("title", "Untitled")
            return f"<h3>{title}</h3>\n{content}"

        return None
    except Exception as E:
        print(E)

def highlight_externalid(html_content):
    try:
        pattern = re.compile(
            r'(<[^>]*data-externalid="(?P<id>[^"]+)"[^>]*>)(?P<text>.*?)</[^>]+>', 
            re.DOTALL | re.IGNORECASE
        )
        
        def html_to_tooltip_text(html_fragment):
            soup = BeautifulSoup(html_fragment, "html.parser")
            for tag in soup.find_all(["script", "style"]):
                tag.decompose()
            return str(soup).strip()
        def repl(match):
            full_tag, external_id, inner_text = match.group(1), match.group(2), match.group(3)
            result = get_tooltip_panel_content(external_id)
            if not result:
                return match.group(0)
            if not inner_text and result.strip().startswith("<ac:image"):
                return result
            if inner_text and result.strip().startswith("<ac:image"):
                return f"{inner_text}{result}"
            tooltip_text = html_to_tooltip_text(result)
            return f'''
        {inner_text}
        <ac:structured-macro ac:name="tooltip" ac:schema-version="1" ac:local-id="tooltip-{external_id}" ac:macro-id="tooltip-{external_id}">
        <ac:parameter ac:name="linkText">{inner_text}</ac:parameter>
        <ac:rich-text-body>
            {tooltip_text}
        </ac:rich-text-body>
        </ac:structured-macro>
        '''.strip()
        return pattern.sub(repl, html_content)

    except Exception as e:
        print("Error in highlight_externalid:", e)
        return html_content

def download_images_from_html_and_update_content(html_content):
    try:    
        soup = BeautifulSoup(html_content, "html.parser")
        img_tags = list(soup.find_all("img"))
        for img_tag in img_tags:
            item_id = img_tag.get("itemid")
            if not item_id:
                continue
            url = f'https://rest.opt.knoiq.co/api/v2/resources/images/{item_id}'
            response = requests.get(url, headers=headers_1)
            if response.status_code == 200:
                os.makedirs(images_folder, exist_ok=True)
                filename = f"{item_id}.png"
                filepath = os.path.join(images_folder, filename)
                with open(filepath, "wb") as f:
                    f.write(response.content)
                image_macro = generate_image_macro_img(filename)
                img_tag.replace_with(BeautifulSoup(image_macro, "html.parser"))
            else:
                print(f"Failed to download image {item_id}. Status code: {response.status_code}")
        return str(soup)
    except Exception as E:
        print(E)

def extract_shared_content(data):
    shared_content = []

    def recurse_children(children):
        for child in children:
            try:
                detail = child.get("detail", {})
                if detail.get("itemType") == "SharedParagraph":
                    fields = child.get("fields", [])
                    title_value = ""
                    value = ""

                    for field in fields:
                        if field.get("name") == "ParagraphTitle":
                            title_value = field.get("value")
                        if field.get("name") == "Text":
                            value = field.get("value")

                    if title_value and value:
                        if 'data-externalid="' in value:
                            value = highlight_externalid(value)
                            print("value of imgId",value)
                        value= download_images_from_html_and_update_content(value)
                        existing_page = get_page_by_title(shared_paragraph_space_key,title_value)
                        if not existing_page:
                            shared_content.append({
                                "title": title_value,
                                "content": value
                            })

                            try:
                                print("body of sp",value)
                                page_id = create_page(shared_paragraph_space_key, title_value, value)
                                uploaded = []
                                try:
                                    for file in os.listdir(images_folder):
                                        file_path_full = os.path.join(images_folder, file)
                                        print("filepathfull",file_path_full)
                                        print(page_id,"page_id")
                                        attach_file(page_id, file_path_full, file)
                                        uploaded.append(file)
                                except Exception as e:
                                    print(e)
                                current_version = get_current_version(page_id)
                                print("current_version",current_version)
                                if current_version is not None:
                                    update_page(page_id, title_value,value, current_version)
                                else:
                                    print(f"Could not fetch version for {title_value}")

                            except Exception as e:
                                print(f"Failed to create page '{title_value}': {e}")
                if "children" in child:
                    recurse_children(child["children"])
            except Exception as e:
                print(f"Error processing child: {e}")

    try:
        recurse_children(data.get("children", []))
        return shared_content
    except Exception as e:
        print(e)
 
extract_macro = extract_shared_content(data)
html_parts = []

def includePagemacro(data):
    try:
        include_blocks = ""
        def recurse_children(children):
            nonlocal include_blocks
            for child in children:
                try:
                    detail = child.get("detail", {})
                    if detail.get("itemType") == "SharedParagraph":
                        fields = child.get("fields", [])
                        title_value = ""
                        for field in fields:
                            if field.get("name") == "ParagraphTitle":
                                title_value = field.get("value")
                        if not title_value:
                            title_value = detail.get("title")
                        if title_value:
                            existing_page=get_page_by_title(shared_paragraph_space_key, title_value)
                            if existing_page:
                                include_block = f'''
<ac:structured-macro ac:name="include" ac:schema-version="1">
  <ac:parameter ac:name="">
    <ac:link>
      <ri:page ri:space-key="{shared_paragraph_space_key}" ri:content-title="{title_value}" />
    </ac:link>
  </ac:parameter>
</ac:structured-macro>
'''
                                include_blocks += include_block
                            else:
                                print(f"Page '{title_value}' not found in Confluence.")
                    if "children" in child:
                        recurse_children(child["children"])
                except Exception as e:
                    print(f"Error processing child: {e}")
        if isinstance(data, dict) and "children" in data:
            recurse_children(data["children"])
        elif isinstance(data, list):
            recurse_children(data)

        return include_blocks
    except Exception as e:
        print("[:x:] Unexpected error during include macro generation:", str(e))
        return None


def extract_content_from_fields(child):
    try:
        fields = child.get("fields", [])
        item_type = child.get("detail", {}).get("itemType")
        if item_type == "SharedParagraph":
            include_macro = includePagemacro({"children": [child]})  # Wrap child into fake root
            if include_macro:
                html_parts.append(include_macro)
        else:
            link_text = None
            hidden_text = None
            
            for field in fields:
                name = field.get("name")
                value = field.get("value", "")

                if name == "LinkText":
                    link_text = value
                elif name == "HiddenText":
                    hidden_text = value
                elif name in ["Text", "VisibleText"]:
                    if value:
                        html_parts.append(value)

            if link_text and hidden_text:
                expand_macro = f"""
        <ac:structured-macro ac:name="expand">
        <ac:parameter ac:name="title">{link_text}</ac:parameter>
        <ac:rich-text-body>
            {hidden_text}
        </ac:rich-text-body>
        </ac:structured-macro>
        """
                html_parts.append(expand_macro)
    except Exception as E:
        print(E)

def recurse_children(children):
    try:
        for child in children:
            if "fields" in child:
                extract_content_from_fields(child)
            if "children" in child and child["children"]:
                recurse_children(child["children"])
    except Exception as E:
        print(E)
        
if "fields" in data:
    extract_content_from_fields(data)
if "children" in data:
    recurse_children(data["children"])
html_content = "\n".join(html_parts)

def find_fragment_in_soup(soup, html_fragment):
    try:
        fragment_soup = BeautifulSoup(html_fragment, 'html.parser')
        fragment_elements = list(fragment_soup.contents)
        if not fragment_elements:
            return None

        for fragment_el in fragment_elements:
            candidates = soup.find_all(fragment_el.name)
            for candidate in candidates:
                if str(candidate) == str(fragment_el):
                    return candidate

        return None
    except Exception as E:
        print(E)
        
def generate_confluence_storage_format(html_content, data):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        links = soup.find_all('a', href=re.compile(r'^#\w+$'))
        bookmarks_in_html = {link['href'][1:] for link in links}  # Set of bookmark names
        processed_bookmarks = set()
        back_to_top_link = soup.find('a', href='#PageTop')
        if back_to_top_link:
            if not soup.find('ac:structured-macro', {'ac:name': 'anchor'}):
                anchor_macro = soup.new_tag('ac:structured-macro', **{'ac:name': 'anchor'})
                param = soup.new_tag('ac:parameter', **{'ac:name': ''})
                param.string = 'PageTop'
                anchor_macro.append(param)
                if soup.body:
                    soup.body.insert(0, anchor_macro)
                else:
                    soup.insert(0, anchor_macro)
        for item in data.get('children', []):
            bookmark = next(
                (f['value'] for f in item.get('fields', []) if f.get('name') == 'Bookmark' and f.get('value')),
                None
            )
            if not bookmark:
                continue
            if bookmark not in bookmarks_in_html:
                continue
            if bookmark in processed_bookmarks:
                continue
            processed_bookmarks.add(bookmark)
            anchor_macro = soup.new_tag('ac:structured-macro', **{'ac:name': 'anchor'})
            param = soup.new_tag('ac:parameter', **{'ac:name': ''})
            param.string = bookmark
            anchor_macro.append(param)
            inserted = False
            for child in item.get('children', []):
                for f in child.get('fields', []):
                    text_value = f.get('value')
                    if not text_value:
                        continue
                    matched_element = find_fragment_in_soup(soup, text_value)
                    if matched_element:
                        matched_element.insert_before(anchor_macro)
                        inserted = True
                        break
                if inserted:
                    break
            if not inserted:
                if soup.body:
                    soup.body.append(anchor_macro)
                else:
                    soup.append(anchor_macro)

        return str(soup)
    except Exception as e:
        print(f"Error in generate_confluence_storage_format: {e}")
        return None

html_content = highlight_externalid(html_content)
html_content = download_images_from_html_and_update_content(html_content)
html_content=generate_confluence_storage_format(html_content, data)
soup = BeautifulSoup(html_content, 'html.parser')
external_links = soup.find_all('a', class_='externallink')
data_itemid = set()
for link in external_links:
    itemid = link.get('data-itemid')
    if itemid:
        data_itemid.add(itemid)
itemid_to_conf={}
for itemid in data_itemid:
    pagefetch_url=f"https://rest.opt.knoiq.co/api/v2/admin/documents/{itemid}"
    response=requests.get(pagefetch_url,headers=headers_1)
    if response.status_code == 200:
        try:
            data = response.json()
            fields = data.get("fields", []) 
            title_1 = next((f.get("value", "Untitled Page") for f in response.json().get("fields", []) if f.get("name") == "DocumentTitle"), "Untitled Page")
            results = get_page_by_title(space_key, title_1)
            if results:
                itemid_to_conf[itemid] = title_1
        except ValueError:
            print("Failed to parse JSON.")
    else:
        print("page not exists",itemid)
for link in external_links:
    itemid = link.get('data-itemid')
    anchor_text = link.text.strip()
    if itemid in itemid_to_conf:
        conf_title = itemid_to_conf[itemid]

        ac_link = soup.new_tag("ac:link")
        ri_page = soup.new_tag("ri:page")
        ri_page['ri:content-title'] = conf_title
        link_body = soup.new_tag("ac:link-body")
        span = soup.new_tag("span")
        span.string = anchor_text
        link_body.append(span)
        ac_link.append(ri_page)
        ac_link.append(link_body)  
        link.replace_with(ac_link)
html_content = str(soup)    
# print("final_html_content",html_content)
   
try:
    page_id=create_page(space_key, title, html_content)
    print(f"Page created: {title}")
except Exception as e:
    print(f"Failed to create page '{title}': {e}")

if page_id:
    uploaded = []

    # STEP 2: Upload images
    for file in os.listdir(images_folder):
        file_path_full = os.path.join(images_folder, file)
        try:
            print(file,"filepathname")
            if file != "2e6d82ef-524c-ea11-a960-000d3ad095fb.png":
                attach_file(page_id, file_path_full, file)
                uploaded.append(file)
            else:
                continue
        except Exception as e:
            print(f"Failed to upload {file}: {e}")
    
    current_version = get_current_version(page_id)
    if current_version:
        update_page(page_id, title, html_content, current_version)

for file in os.listdir(images_folder):
    try:
        os.remove(os.path.join(images_folder, file))
    except Exception as e:
        print(f"Failed to delete {file}: {e}")
   
