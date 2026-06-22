import re

with open('/home/alyan-hammad/tanzeem_webapp/templates/approval_requests.html', 'r') as f:
    content = f.read()

# Extract the modal template block
modal_pattern = re.compile(r'(                            <!-- Action Modal -->\n                            <div class="modal fade".*?                            </div>\n)', re.DOTALL)

match = modal_pattern.search(content)
if match:
    modal_str = match.group(1)
    # Remove it from inside the loop
    content = content.replace(modal_str, '')
    
    # We need to add it outside the table.
    # Find the end of the pending tab:
    end_of_pending_pattern = r'                        </tbody>\n                    </table>\n                </div>\n            </div>\n        </div>\n'
    
    # Create the new modals block wrapped in a loop
    new_modals_block = f'                        </tbody>\n                    </table>\n                </div>\n            </div>\n        </div>\n\n        <!-- Action Modals -->\n        {{% for req in pending_requests %}}\n{modal_str}        {{% endfor %}}\n'
    
    content = content.replace(end_of_pending_pattern, new_modals_block)
    
    with open('/home/alyan-hammad/tanzeem_webapp/templates/approval_requests.html', 'w') as f:
        f.write(content)
    print("Fixed!")
else:
    print("Modal not found")

