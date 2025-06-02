import json
import os
import re
import chardet
from bs4 import BeautifulSoup
from atlassian import Confluence
import requests
from bs4 import NavigableString
from dotenv import load_dotenv
import os
import requests
import binascii
import os
from Crypto.Hash import SHA256, HMAC

# file_path = "output.json"
images_folder = "images"
space_key = 'KMT'

# Load variables from .env into the environment
load_dotenv()

#knosys authentication
BASE_URL = "https://rest.opt.knoiq.co/api/v1"

# Credentials
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN") # Public access key
SITE_ID = os.getenv("SITE_ID")  # KnowledgeIQ site ID
USER_TYPE = "Admin"  # Either 'admin' or 'public'
SECRET_KEY = os.getenv("SECRET_KEY")
def get_auth_challenge():
    """Step 1: Request an Authentication Challenge"""
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
def generate_signature(challenge_token):
    """Generate HMAC-SHA256 signature and encode it in Base64"""
    """Step 2: Generate HMAC-SHA256 signature and encode it in Base64"""
    # Base 64 - Encoding the secret key.
    hex_bytes = bytes.fromhex(SECRET_KEY)
    secret_b64 = binascii.b2a_base64(hex_bytes).decode("utf-8").strip()
    # Generate the challenge signature
    secret_key_encoded = binascii.a2b_base64(secret_b64)
    hash_value = HMAC.new(secret_key_encoded, challenge_token.encode("utf-8"), digestmod=SHA256)
    signature = binascii.b2a_base64(hash_value.digest()).decode("utf-8").strip()
    return signature
def get_auth_token(challenge_token, signature):
    """Step 3: Exchange the challenge and signature for an authentication token"""
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
        # print(f"Token received: {auth_token}")
        return auth_token
   
    else:
        print("[:x:] Authentication failed:", response.text)
        return None
challenge = get_auth_challenge()
# print(challenge)
if challenge:
    # print(f"Returned Challenge {challenge}")
    signature = generate_signature(challenge)
    # print(signature)
    auth_token = get_auth_token(challenge, signature)
    # print(f"Returned Token {auth_token}")
    
Document_Id=""
confluence_email =" "
  
# Get values from environment
source_url=os.getenv("source_url")
headers_1={"Content-Type":"application/json", "Authorization":f"Bearer {auth_token}"}

def get_document_title(fields):
    for field in fields:
        if field.get("name") == "DocumentTitle":
            # return re.sub(r'[<>:"/\\|?*]', '', field.get("value", "Untitled Page"))
            return field.get("value","Untitled Page")
    return "Untitled Page"

def getuserEmail(created_by):
    with open("users.json", "r") as f:
        email_map = json.load(f)
    def get_confluence_email(kiq_email):
        return email_map.get(kiq_email, "Not found")
    return get_confluence_email(created_by)

#Source pages fetching 
response=requests.get(source_url,headers=headers_1)
if response.status_code == 200:
    try:
        data = response.json()
        fields = data.get("fields", []) 
        Document_Id = data['detail']['id']
        Created_by=data['detail']['createdByPerson']
        print(Document_Id,Created_by)
        confluence_email=getuserEmail(Created_by)
        print("Mapped email:", confluence_email)
        title = get_document_title(fields)
        print("Document Title:", title)
    except ValueError:
        print("Failed to parse JSON.")
else:
    print(f"Request failed with status code: {response.status_code}")

url = os.getenv("CONFLUENCE_URL")
api_token = os.getenv("CONFLUENCE_API_TOKEN")

# Authenticate with Confluence
# print(url,"confemail:",confluence_email,"password:",api_token)
confluence = Confluence(
    url=url,
    username=confluence_email,
    password=api_token
)

# Step 3: Build info_lookup map from external information
external_info_list = data.get("external", {}).get("information", [])
info_lookup = {item["informationId"]: item for item in external_info_list if "informationId" in item}

# Step 4: Content building
html_parts = []

def extract_content_from_fields(fields):
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

def recurse_children(children):
    for child in children:
        if "fields" in child:
            extract_content_from_fields(child["fields"])
        if "children" in child and child["children"]:
            recurse_children(child["children"])

if "fields" in data:
    extract_content_from_fields(data["fields"])
if "children" in data:
    recurse_children(data["children"])

html_content = "\n".join(html_parts)

# Step 5: Image macro logic
def generate_image_macro(filename):
    return f'''
<ac:image ac:height="20" ac:width="30" >
  <ri:attachment ri:filename="{filename}"/>
</ac:image>
'''.strip()

def generate_image_macro_img(filename):
    return f'''
<ac:image>
  <ri:attachment ri:filename="{filename}"/>
</ac:image>
'''.strip()

from bs4 import BeautifulSoup
import re

def find_fragment_in_soup(soup, html_fragment):
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

# def find_all_fragments_in_soup(soup, html_fragment):
#     fragment_soup = BeautifulSoup(html_fragment, 'html.parser')
#     fragment_elements = list(fragment_soup.contents)
#     if not fragment_elements:
#         return []

#     matched_elements = []
#     for fragment_el in fragment_elements:
#         candidates = soup.find_all(fragment_el.name)
#         for candidate in candidates:
#             if str(candidate).strip() == str(fragment_el).strip():
#                 matched_elements.append(candidate)
#     return matched_elements

def generate_confluence_storage_format(html_content, ddata):
    """
    Insert <ac:structured-macro ac:name="anchor"><ac:parameter>{bookmark}</ac:parameter></ac:structured-macro>
    before the first matching text element in the HTML, for bookmarks found in both ddata and the HTML links.

    :param html_content: Original HTML content string.
    :param ddata: Dictionary containing items with 'fields' that may include 'Bookmark' values.
    :return: Modified HTML string suitable for Confluence storage format.
    """
    # soup = BeautifulSoup(html_content, 'html.parser')
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find all anchor links with href="#bookmark"
    links = soup.find_all('a', href=re.compile(r'^#\w+$'))
    print("links",links)
    bookmarks_in_html = {link['href'][1:] for link in links}  # Set of bookmark names

    processed_bookmarks = set()
    back_to_top_link = soup.find('a', href='#PageTop')
    if back_to_top_link:
    # Check if an element with id="PageTop" exists
        if not soup.find('ac:structured-macro', {'ac:name': 'anchor'}):
    # Insert Confluence anchor macro <ac:structured-macro ac:name="anchor"><ac:parameter ac:name="">PageTop</ac:parameter></ac:structured-macro>
            anchor_macro = soup.new_tag('ac:structured-macro', **{'ac:name': 'anchor'})
            param = soup.new_tag('ac:parameter', **{'ac:name': ''})
            param.string = 'PageTop'
            anchor_macro.append(param)

            if soup.body:
                soup.body.insert(0, anchor_macro)
            else:
                soup.insert(0, anchor_macro)

            print("Inserted Confluence anchor macro for PageTop at the top of the page.")

    for item in ddata.get('children', []):
        # Extract bookmark value from item fields
        bookmark = next(
            (f['value'] for f in item.get('fields', []) if f.get('name') == 'Bookmark' and f.get('value')),
            None
        )
        print("Bookmark",bookmark)
        if not bookmark:
            continue
        if bookmark not in bookmarks_in_html:
            continue
        if bookmark in processed_bookmarks:
            continue

        processed_bookmarks.add(bookmark)

        # Create Confluence anchor macro element
        anchor_macro = soup.new_tag('ac:structured-macro', **{'ac:name': 'anchor'})
        param = soup.new_tag('ac:parameter', **{'ac:name': ''})
        param.string = bookmark
        anchor_macro.append(param)

        inserted = False

        # Try to find text in HTML matching child fields and insert anchor before it
        for child in item.get('children', []):
            for f in child.get('fields', []):
                text_value = f.get('value')
                # matched_element = find_fragment_in_soup(soup, text_value)
                # print("matchedelement",matched_element)
                # print("text_value",text_value)
                if not text_value:
                    continue

                matched_element = find_fragment_in_soup(soup, text_value)
                if matched_element:
                    matched_element.insert_before(anchor_macro)
                    print(f"Inserted anchor macro before matched element for bookmark: {bookmark}")
                    inserted = True
                    break  
            if inserted:
                break

        # Fallback: if no matching text found, append anchor at end of <body> or root
        if not inserted:
            if soup.body:
                soup.body.append(anchor_macro)
            else:
                soup.append(anchor_macro)
            print(f"Inserted anchor macro at the end for bookmark: {bookmark}")

    return str(soup)
def get_tooltip_panel_content(external_id):
    entry = info_lookup.get(external_id)
    if not entry:
        return None

    info_type = entry.get("informationType")
    content = entry.get("content", "")

    def fetch_and_save_image(item_id):
        url = f'https://rest.opt.knoiq.co/api/v2/resources/images/{item_id}'
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            os.makedirs(images_folder, exist_ok=True)
            filepath = os.path.join(images_folder, f"{item_id}.png")
            with open(filepath, "wb") as f:
                f.write(response.content)
            print(f"Image saved to {filepath}")
            return filepath
        else:
            print(f"Failed to fetch image {item_id}. Status code: {response.status_code}")
            return None

    # Case 1: Handle 'Image / screenshot' content
    if info_type == "Image / screenshot":
        soup = BeautifulSoup(content, "html.parser")
        img_tag = soup.find("img")
        if img_tag and img_tag.get("itemid"):
            item_id = img_tag["itemid"]
            filepath = fetch_and_save_image(item_id)
            if filepath:
                return generate_image_macro(os.path.basename(filepath))
        return None

    # Case 2: Handle HTML content with embedded <img> tags
    if info_type is None or info_type == "HTML":
        soup = BeautifulSoup(content, "html.parser")
        img_tags = soup.find_all("img")
        for img_tag in img_tags:
            item_id = img_tag.get("itemid")
            if item_id:
                filepath = fetch_and_save_image(item_id)
                if filepath:
                    return generate_image_macro(os.path.basename(filepath))

        # If no valid image found, return the raw content
        title = entry.get("title", "Untitled")
        return f"<h3>{title}</h3>\n{content}"

    return None

def highlight_externalid(html_content):
    pattern = re.compile(
        r'(<[^>]*data-externalid="([^"]+)"[^>]*>)(.*?)</[^>]+>',
        re.DOTALL | re.IGNORECASE
    )
    
    def html_to_tooltip_text(html_fragment):
        soup = BeautifulSoup(html_fragment, "html.parser")

    # Optional: remove problematic tags
        for tag in soup.find_all(["script", "style"]):
           tag.decompose()

        return str(soup).strip()


    def repl(match):
        _, external_id, inner_text = match.group(1), match.group(2), match.group(3)
        result = get_tooltip_panel_content(external_id)

        if not result:
            return match.group(0)

        if result.strip().startswith("<ac:image"):
            return result

        tooltip_text = html_to_tooltip_text(result)
        return f'''
<ac:structured-macro ac:name="tooltip" ac:schema-version="1" ac:local-id="tooltip-{external_id}" ac:macro-id="tooltip-{external_id}">
  <ac:parameter ac:name="linkText">{inner_text.strip()}</ac:parameter>
  <ac:rich-text-body>
    {tooltip_text}
  </ac:rich-text-body>
</ac:structured-macro>
'''.strip()

    return pattern.sub(repl, html_content)

html_content = highlight_externalid(html_content)

# def add_dynamic_step_anchors(html_content):
#     # Match headers that start with "Step X:" where X is any number
#     pattern = re.compile(
#         r'(<h[1-6][^>]*>)(Step\s*(\d+):)(.*?)</h[1-6]>',
#         re.IGNORECASE | re.DOTALL
#     )
    
#     def replacer(match):
#         header_tag = match.group(1)     
#         step_text = match.group(2)      
#         step_number = match.group(3)    
#         rest_of_header = match.group(4).strip()  

#         # Generate the anchor macro dynamically
#         anchor_macro = f'''
# <ac:structured-macro ac:name="anchor">
#   <ac:parameter ac:name="">s{step_number}</ac:parameter>
# </ac:structured-macro>'''.strip()

#         # Create the new header content with <b> tags
#         bolded_header = f"<b>{step_text} {rest_of_header}</b>"

#         # Build the final replacement
#         # Close header tag with </h3>, but use the same level as opening tag
#         closing_tag = '</' + header_tag[1] + '>'

#         return f"{anchor_macro}\n{header_tag}{bolded_header}{closing_tag}"

#     updated_html = pattern.sub(replacer, html_content)

#     return updated_html

def download_images_from_html_and_update_content(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    img_tags = soup.find_all("img")

    for img_tag in img_tags:
        item_id = img_tag.get("itemid")
        if not item_id:
            continue

        # Download the image
        url = f'https://rest.opt.knoiq.co/api/v2/resources/images/{item_id}'
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            os.makedirs(images_folder, exist_ok=True)
            filepath = os.path.join(images_folder, f"{item_id}.png")
            with open(filepath, "wb") as f:
                f.write(response.content)
            print(f"Image saved to {filepath}")

            # Generate the <ac:image> macro
            image_macro = generate_image_macro_img(os.path.basename(filepath))

            # Replace <img> tag with the Confluence image macro
            img_tag.replace_with(BeautifulSoup(image_macro, "html.parser"))
        else:
            print(f"Failed to download image {item_id}. Status code: {response.status_code}")

    # Return the updated HTML with image macros *inline*
    return str(soup)

html_content = download_images_from_html_and_update_content(html_content)
html_content=generate_confluence_storage_format(html_content, data)
soup = BeautifulSoup(html_content, 'html.parser')

external_links = soup.find_all('a', class_='externallink')
data_itemid = set()

# def add_dynamic_step_anchors_with_targets(html_content, json_data):
#     soup = BeautifulSoup(html_content, 'html.parser')
#     links = soup.find_all('a', href=True)
#     pattern = re.compile(r'^#\w+$')
#     created_sections = set()

#     for link in links:
#         href = link['href'].strip()
#         if pattern.match(href):
#             bookmark_value = href[1:]  # remove the "#"
#             if bookmark_value in created_sections:
#                 continue
#             created_sections.add(bookmark_value)

#             # Find matching content in JSON
#             children = json_data.get('children', [])
#             for item in children:
#                 for field in item.get('fields', []):
#                     if field.get('name') == 'Bookmark' and field.get('value') == bookmark_value:
#                         # Insert anchor macro at the top of the body or in a section
#                         anchor_macro = soup.new_tag("ac:structured-macro", **{"ac:name": "anchor"})
#                         parameter = soup.new_tag("ac:parameter", **{"ac:name": ""})
#                         parameter.string = bookmark_value
#                         anchor_macro.append(parameter)
#                         # Insert target content
#                         text_values = []
#                         if item.get('children'):
#                             for child in item['children']:
#                                 for f in child.get('fields', []):
#                                     val = f.get('value')
#                                     text_values.append(val)
#                                     p_tag = soup.new_tag("p")
#                                     p_tag.string = val
#                                     anchor_macro.append(p_tag)

#                         inserted = False
#                         for val in text_values:
#                             matching_elements = soup.find_all(string=val)
#                             for element in matching_elements:
#                                 element_parent = element.parent
#                                 element_parent.insert_before(anchor_macro)
#                                 inserted = True

#                         if inserted:
#                             break

#     return str(soup)

# html_content=add_dynamic_step_anchors_with_targets(html_content,data)

for link in external_links:
    # print("Anchor text:", link.text.strip())
    itemid = link.get('data-itemid')
    if itemid:
        data_itemid.add(itemid)
        # print(itemid)
itemid_to_conf={}
for itemid in data_itemid:
    pagefetch_url=f"https://rest.opt.knoiq.co/api/v2/admin/documents/{itemid}"
    response=requests.get(pagefetch_url,headers=headers_1)
    if response.status_code == 200:
        try:
            data = response.json()
            fields = data.get("fields", []) 
            title_1 = get_document_title(fields)
            # print("page title",title_1)
            results = confluence.get_page_by_title(space_key, title_1)
            if results:
                itemid_to_conf[itemid] = title_1
                print(itemid_to_conf)
            # print(results)
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
        # plain_body = soup.new_tag("ac:plain-text-link-body")
        # # plain_body.string = anchor_text
        # plain_body.append(NavigableString(f"<![CDATA[{anchor_text}]]>"))
        link_body = soup.new_tag("ac:link-body")
        span = soup.new_tag("span")
        span.string = anchor_text
        link_body.append(span)
        ac_link.append(ri_page)
        # ac_link.append(plain_body)
        ac_link.append(link_body)  
        link.replace_with(ac_link)

# Final HTML
html_content = str(soup)    
    
# print(html_content)
# Step 6: Create page
try:
    result = confluence.create_page(
        space=space_key,
        title=title,
        body=html_content,
        representation='storage'
    )
    print(f"✅ Page created: {result['_links']['base']}{result['_links']['webui']}")
except Exception as e:
    print(f"Failed to create Confluence page: {e}")
    exit()

# Step 7: Upload images to the created page
page_id = result["id"]
uploaded = []

for file in os.listdir(images_folder):
    file_path_full = os.path.join(images_folder, file)
    try:
        confluence.attach_file(
            filename=file_path_full,
            name=file,
            content_type='image/png',
            page_id=page_id
        )
        uploaded.append(file)
    except Exception as e:
        print(f"Failed to upload {file}: {e}")
for file in uploaded:
    image_tag = f'<ac:image><ri:attachment ri:filename="{file}" /></ac:image><br/>'
    html_content += image_tag
    
confluence.update_page(
    page_id=page_id,
    title=title,
    body=html_content,
    representation='storage'
)

print(f"📷 Uploaded {len(uploaded)} images: {uploaded}")
for file in os.listdir(images_folder):
    try:
        os.remove(os.path.join(images_folder, file))
    except Exception as e:
        print(f"Failed to delete {file}: {e}")
      
TRACKING_PAGE_ID = "157745519"  # Confluence page to be updated
NEW_PAGE_ID = page_id      

# Step 2: Get current content of tracking page
tracking_page = confluence.get_page_by_id(TRACKING_PAGE_ID, expand='body.storage,version')
current_body = tracking_page['body']['storage']['value']

# Step 3: Construct new row with hyperlink
new_row = f'''
<tr>
  <td>{Document_Id}</td>
  <td>{title}</td>
  <td><a href="https://elabor8demo.atlassian.net/wiki/spaces/{space_key}/pages/{NEW_PAGE_ID}">{NEW_PAGE_ID}</a></td>
</tr>
'''

# Step 4: Insert before </tbody>
if "</tbody>" in current_body:
    updated_body = current_body.replace("</tbody>", new_row + "</tbody>")
else:
    print("❌ Could not locate </tbody> in tracking page.")
    exit()

# Step 5: Update the Confluence page
try:
    confluence.update_page(
        page_id=TRACKING_PAGE_ID,
        title=tracking_page['title'],
        body=updated_body,
        representation='storage',
        minor_edit=True
    )
    print(f"✅ Confluence tracking page updated with: {Document_Id}, {NEW_PAGE_ID}")
except Exception as e:
    print(f"❌ Failed to update tracking page: {e}")

