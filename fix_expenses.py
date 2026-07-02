import re

with open('templates/expenses.html', 'r') as f:
    content = f.read()

# 1. Close table early
content = content.replace(
    '</tr>\n\n                    <!-- Expense Voucher Modal -->',
    '</tr>\n                    {% endfor %}\n                </tbody>\n            </table>\n        </div>\n\n        {% for expense in expenses %}\n                    <!-- Expense Voucher Modal -->'
)

# 2. Remove the old else block and endfor
old_end_block = """                    {% endif %}
                    {% else %}
                    <tr>
                        <td colspan="7" class="text-center py-4">No expenses found.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>"""
content = content.replace(old_end_block, "                    {% endif %}\n                    {% endfor %}")

with open('templates/expenses.html', 'w') as f:
    f.write(content)
