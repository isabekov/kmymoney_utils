#! /usr/bin/python3
# Utilities for batch editing a KMyMoney file
# Functionality: check the help message
# License: GPL v3.0
# Author: Altynbek Isabekov

import xml.etree.ElementTree as ET
import sys
import re
import getopt

# Account types are defined in:
# Repo: https://invent.kde.org/office/kmymoney
# File: kmymoney/mymoney/mymoneyenums.h

AccountTypes = {
    "Unknown": 0,  # For error handling
    "Checkings": 1,  # Standard checking account
    "Savings": 2,  # Typical savings account
    "Cash": 3,  # Denotes a shoe-box or pillowcase stuffed with cash
    "CreditCard": 4,  # Credit card accounts
    "Loan": 5,  # Loan and mortgage accounts (liability)
    "CertificateDep": 6,  # Certificates of Deposit
    "Investment": 7,  # Investment account
    "MoneyMarket": 8,  # Money Market Account
    "Asset": 9,  # Denotes a generic asset account.*/
    "Liability": 10,  # Denotes a generic liability account.*/
    "Currency": 11,  # Denotes a currency trading account.
    "Income": 12,  # Denotes an income account
    "Expense": 13,  # Denotes an expense account
    "AssetLoan": 14,  # Denotes a loan (asset of the owner of this object)
    "Stock": 15,  # Denotes an security account as sub-account for an investment
    "Equity": 16,  # Denotes an equity account e.g. opening/closing balance
}

AccountTypesInv = {v: k for k, v in AccountTypes.items()}

AccountRenaming = {"Asset": "Assets", "Liability": "Liabilities", "Expense": "Expenses"}


def traverse_account_hierarchy_backwards(accounts, acnt_id):
    if accounts[acnt_id]["parentaccount"] == "":
        acnt_name = accounts[acnt_id]["name"]
        if acnt_name in AccountRenaming.keys():
            acnt_name = AccountRenaming[acnt_name]
        return acnt_name
    else:
        parent_acnt_name = traverse_account_hierarchy_backwards(
            accounts, accounts[acnt_id]["parentaccount"]
        )
    acnt_name = accounts[acnt_id]["name"]
    return f"{parent_acnt_name}:{acnt_name}"


def find_mismatches_in_slits(transactions, accounts, payees, split_type):
    cnt_all = 0
    cnt_emp = 0
    for i, item in enumerate(transactions):
        txn_id = item.attrib["id"]
        date = item.attrib["postdate"]
        splits = item.findall("./SPLITS/SPLIT")
        # Source account
        src = splits[0].attrib
        src_acnt_id = src["account"]
        src_acnt_type = AccountTypesInv[int(accounts[src_acnt_id]["type"])]
        src_acnt_name = traverse_account_hierarchy_backwards(accounts, src_acnt_id)
        src_acnt_currency = accounts[src_acnt_id]["currency"]
        src_amount = eval(src["price"]) * eval(src["value"])
        src_memo = src["memo"]
        src_payee_id = splits[0].attrib["payee"]
        if src_payee_id != "":
            src_payee_name = payees[src_payee_id]["name"]
        else:
            src_payee_name = ""
        # Check transaction with two splits (most of the transactions are of this type)
        if (split_type == "2") and (len(list(splits)) == 2):
            # Destination account
            dst = splits[1].attrib
            dst_payee_id = dst["payee"]
            dst_acnt_id = dst["account"]
            dst_acnt_type = AccountTypesInv[int(accounts[dst_acnt_id]["type"])]
            dst_acnt_name = traverse_account_hierarchy_backwards(accounts, dst_acnt_id)
            dst_acnt_currency = accounts[dst_acnt_id]["currency"]
            dst_amount = eval(dst["price"]) * eval(dst["value"])
            dst_memo = dst["memo"]
            if dst_payee_id != "":
                dst_payee_name = payees[dst_payee_id]["name"]
            else:
                dst_payee_name = ""
            # For a transaction with two splits, destination payee should match source payee.
            # A mismatch is usually caused by an empty destination payee.
            if src_payee_id != dst_payee_id:
                print(f"Transaction {txn_id}")
                print("Source and destination payee mismatch:")
                print(f"Date: {date}")
                print(f"Source payee ID: {src_payee_id}")
                print(f"Source payee: {src_payee_name}")
                print(f"Source account name  : {src_acnt_name}")
                print(f"Source account type  : {src_acnt_type}")
                print(f"Source account amount: {src_amount} {src_acnt_currency}")
                print(f"Source payee memo: {src_memo}")

                print(f"Desti. payee ID: {dst_payee_id}")
                print(f"Desti. payee: {dst_payee_name}")
                print(f"Desti. account name  : {dst_acnt_name}")
                print(f"Desti. account type  : {dst_acnt_type}")
                print(f"Desti. account amount: {dst_amount} {dst_acnt_currency}")
                print(f"Desti. payee memo: {dst_memo}\n")
                cnt_all += 1
                if dst_payee_id == "":
                    # Here an empty destination payee is replaced with transaction's source payee.
                    splits[1].attrib["payee"] = src_payee_id
                    cnt_emp += 1
        elif (split_type == "1") and (len(list(splits)) == 1):
            print(f"Transaction {txn_id}")
            print("No second split!")
            print(f"Date: {date}")
            print(f"Source payee ID: {src_payee_id}")
            print(f"Source payee: {src_payee_name}")
            print(f"Source account name  : {src_acnt_name}")
            print(f"Source account type  : {src_acnt_type}")
            print(f"Source account amount: {src_amount} {src_acnt_currency}")
            print(f"Source payee memo: {src_memo}")
            cnt_all += 1

    if split_type == "2":
        print(f"Count of mismatching source and destination splits: {cnt_all}")
        print(f"Count of transactions with one splits being empty: {cnt_emp}")
    elif split_type == "1":
        print(f"Count of transactions with a single split: {cnt_all}")
    return


def add_default_tag(transactions, accounts, tags, default_tag, excluded_tags):
    excluded_tags_ext = excluded_tags + [default_tag]
    for i, item in enumerate(transactions):
        splits = item.findall("./SPLITS/SPLIT")
        txn_id = item.attrib["id"]
        # Check if any of destination splits is affiliated with "excluded_tags"
        spl_ex_tags = []
        for k in excluded_tags_ext:
            spl_ex_tags = spl_ex_tags + item.findall(f'./SPLITS/SPLIT/TAG[@id="{tags[k]}"]')

        # Check if all destination splits refer to Income or Expense accounts
        if_dst_inc_exp = 0
        dst_acnt_type = {}
        for j, spl in enumerate(splits[1:], 1):
            # Destination account
            dst = spl.attrib
            dst_acnt_id = dst["account"]
            dst_acnt_type[j] = AccountTypesInv[int(accounts[dst_acnt_id]["type"])]
            if_dst_inc_exp =+ (dst_acnt_type[j] in ["Income", "Expense"])

        # If number of splits is 2 (minimal necessary) or more and the splits are not affiliated with
        # "excluded_tags", then assign default tag
        if (len(spl_ex_tags) == 0) and if_dst_inc_exp:
            dt = ET.SubElement(splits[0], "TAG")
            dt.attrib["id"] = tags[default_tag]
        elif (len(splits) > 2):
            for j, spl in enumerate(splits[1:], 1):
                mspl_ex_tags = []
                for k in excluded_tags_ext:
                    mspl_ex_tags = mspl_ex_tags + spl.findall(f'./TAG[@id="{tags[k]}"]')

                if (len(mspl_ex_tags) == 0) & (dst_acnt_type[j] in ["Income", "Expense"]):
                    dt = ET.SubElement(spl, "TAG")
                    dt.attrib["id"] = tags[default_tag]
    return


def replace_tag_in_account(transactions, tags, target_acnt_id, old_tag, new_tag):
    for i, item in enumerate(transactions):
        splits = item.findall("./SPLITS/SPLIT")

        if len(splits) == 2:
            # For two-split transaction, tag is stored at the first split
            if splits[1].attrib["account"] == target_acnt_id:
                dt = splits[0].findall(f'./TAG[@id="{tags[old_tag]}"]')
                if len(dt) > 0:
                    dt[0].attrib["id"] = tags[new_tag]
        else:
            for j, spl in enumerate(splits[1:], 1):
                if spl.attrib["account"] == target_acnt_id:
                    dt = spl.findall(f'./TAG[@id="{tags[old_tag]}"]')
                    if len(dt) > 0:
                        dt[0].attrib["id"] = tags[new_tag]
    return


def move_tag_from_split_level_to_txn_level(transactions, tags, tag_to_move, accounts):
    for i, item in enumerate(transactions):
        splits = item.findall("./SPLITS/SPLIT")

        cnt_inc_exp_acnts = 0
        cnt_tagged_splits = 0
        if len(splits) > 2:
            for j, spl in enumerate(splits[1:], 1):
                acnt = spl.attrib["account"]
                acnt_type = AccountTypesInv[int(accounts[acnt]["type"])]
                if acnt_type in ["Income", "Expense"]:
                    cnt_inc_exp_acnts += 1
                    tagged_spl = spl.findall(f'./TAG[@id="{tags[tag_to_move]}"]')
                    if len(tagged_spl) > 0:
                        cnt_tagged_splits += 1

            if cnt_inc_exp_acnts == cnt_tagged_splits:
                # All income/expense splits possess "tag_to_move"
                is_top_split_tagged = bool(splits[0].findall(f'./TAG[@id="{tags[tag_to_move]}"]'))
                if not is_top_split_tagged:
                    dt = ET.SubElement(splits[0], "TAG")
                    dt.attrib["id"] = tags[tag_to_move]

                for j, spl in enumerate(splits[1:], 1):
                    acnt = spl.attrib["account"]
                    acnt_type = AccountTypesInv[int(accounts[acnt]["type"])]
                    if acnt_type in ["Income", "Expense"]:
                        tagged_spl = spl.findall(f'./TAG[@id="{tags[tag_to_move]}"]')[0]
                        if tagged_spl is not None:
                            spl.remove(tagged_spl)
    return


def erase_number(transactions, to_erase_number):
    for i, item in enumerate(transactions):
        splits = item.findall("./SPLITS/SPLIT")
        for spl in splits:
            spl.attrib["number"] = ""
    return


def fix_reconcile_flag(transactions, reconcile_flag):
    for i, item in enumerate(transactions):
        splits = item.findall("./SPLITS/SPLIT")
        for spl in splits:
            spl.attrib["reconcileflag"] = reconcile_flag
    return


def assign_txn_numbers(root, account):
    splits = sorted(
        root.findall(f'./TRANSACTIONS/TRANSACTION/SPLITS/SPLIT[@account="{account}"]'),
        key=lambda child: (child.tag, child.get("postdate")),
    )
    for count, split in enumerate(splits, start=1):
        split.set("number", str(count))
    return


def reorder_tags_in_txn(transactions, rev_tags):
    for i, item in enumerate(transactions):
        splits = item.findall("./SPLITS/SPLIT")

        for j, spl in enumerate(splits, 1):
            spl[:] = sorted(spl.findall(f'./TAG'), key=lambda child: rev_tags[child.get("id")])
    return


def print_help():
    print(
        f"python3 {sys.argv[0]} [options/flags] [-o <outputfile>] <inputfile>.xml\n"
    )
    print(
        'Input arguments:\n\
    -o --output                          Output file, if not specified, output file is set to\n\
                                         "<input file>_fixed.xml". Input file should always be a KMyMoney XML file.\n\
    -e --erase-txn-numbers               Erase all transaction numbers (i.e. "number" attribute in a split).\n\
    -n --assign-txn-numbers              Assign integer values to all transactions in an account\n\
                                         sorted in chronological order by "post date". The earliest transaction\n\
                                         is assigned number 1, the ones following it will have numbers incremented\n\
                                         by one. Iterate over all asset accounts.\n\
    -s --fix-splits-with-count <count>   If <count> is 2, then fix empty payee for the second split in a transaction\n\
                                         with 2 splits by assigning the payee from the first split.\n\
                                         If <count> is 1, then display transactions with a single split.\n\
                                         In a double-entry accounting system, there have to be two splits in a\n\
                                         transaction for the consistency purpose.\n\
                                         Usually, payees in a transaction with 2 splits should be identical.\n\
                                         Transactions with 1 split should be checked manually, because\n\
                                         even for opening balances the money is transferred from an equity account,\n\
                                         which means the 2nd split must exist and contain equity account information.\n\
    -r --reconcile-flag  <flag>          Assign reconcile <flag> to all splits in all transactions.\n\
                                         <flag> can be equal to -1 (unknown), 0 (not reconciled), 1 (cleared),\n\
                                         2 (reconciled) or 3 (frozen).\n\
    -a --add-tag-if-not-tagged <tag>     Add default tag if it is not present at split/transaction.\n\
                                         under condition that split/condition is not associated with tags in "-x"\n\
                                         option (default tag and excluded tags are mutually exclusive).\n\
    -x --excluded-tags <tag1>,<tag2>     List of exluded tags separated by a comma.\n\
                                         Arguments "-a household_1 -x household_2,household_3" will add default tag\n\
                                         "household_1" to a split/transaction if it is not taged by tags\n\
                                         "household_2" and "household_3".\n\
    -d --replace-tag-with <foo>,<bar>    Replace tag <foo> with tag <bar> in account specified by "--in-account".\n\
    -i --in-account <acnt>               Target account whose transactions(-splits) will have tags replaced.\n\
                                         Arguments \'-i "ExtraHousehold" -d household_1,household_2\' will replace \n\
                                         tag "household_1" with tag "household_2" for transactions in account\n\
                                         "ExtraHousehold". Account name should a substring of the full account name.\n\
    -m --move-split-lvl-tag-to-txn-lvl   Move tag from split level to transaction level if all splits in a the\n\
                                         transaction have this tag assigned. Erase the tag at split level.\n\
    -c --set-expenses-currency <curr>    Set all expense accounts\' currency to <curr>. \n\
    -t --reorder-tags                    Reorder tags in transactions alphabetically.\n\
    -h --help                            Print this help message.\
    '
    )
    return


def main(argv):
    try:
        opts, args = getopt.getopt(
            argv[1:],
            "a:d:hec:i:r:o:m:ns:x:t",
            [
                "add-tag-if-not-tagged=",
                "help",
                "fix-splits-with-count=",
                "erase-txn-numbers",
                "reconcile-flag=",
                "assign-txn-numbers",
                "output=",
                "set-expenses-currency=",
                "excluded-tags",
                "in-account=",
                "replace-tag-with",
                "move-split-lvl-tag-to-txn-lvl",
                "reorder-tags"
            ],
        )
    except getopt.GetoptError:
        print_help()
        sys.exit(2)

    reconcile_flag = None
    to_erase_number = False
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print_help()
            sys.exit()
        elif opt in ("-o", "--output"):
            outputfile = arg
        elif opt in ("-e", "--erase-txn-numbers"):
            to_erase_number = True
        elif opt in ("-a", "--add-tag-if-not-tagged"):
            to_add_default_tag = True
            default_tag = arg
        elif opt in ("-x", "--excluded-tags"):
            to_add_default_tag = True
            excluded_tags = arg.split(",")
        elif opt in ("-s", "--fix-splits"):
            split_type = arg
        elif opt in ("-r", "--reconcile-flag"):
            reconcile_flag = arg
        elif opt in ("-n", "--assign-txn-numbers"):
            set_txn_numbers_flag = True
        elif opt in ("-c", "--set-expenses-currency"):
            set_expenses_currency_flag = True
            expenses_currency = arg
        elif opt in ("-i", "--in-account"):
            set_replace_tag_in_account_flag = True
            replace_target_account = arg
        elif opt in ("-d", "--replace-tag-with"):
            set_replace_tag_in_account_flag = True
            old_tag, new_tag = arg.split(",")
        elif opt in ("-m", "--move-split-lvl-tag-to-txn-lvl"):
            set_move_split_lvl_tag_to_txn_lvl = True
            tag_to_move = arg
        elif opt in ("-t", "--reorder-tags"):
            to_reorder_tags = True

    if len(args) == 1:
        inputfile = args[0]

    if not ("outputfile" in vars()):
        tokens = inputfile.split(".")
        outputfile = f"{''.join(tokens[:-1])}_fixed.{tokens[-1]}"

    # ============== PARSING XML ================
    parser = ET.XMLParser(encoding="utf-8")
    tree = ET.parse(inputfile, parser=parser)
    root = tree.getroot()

    # ============== ACCOUNTS ===================
    accounts = dict()
    for k in root.findall("./ACCOUNTS/ACCOUNT"):
        accounts[k.attrib["id"]] = k.attrib

    # ============== PAYEES =====================
    payees = dict()
    for k in root.findall("./PAYEES/PAYEE"):
        payees[k.attrib["id"]] = k.attrib

    # ================ TAGS =====================
    tags = dict()
    for k in root.findall("./TAGS/TAG"):
        tags[k.attrib["name"]] = k.attrib["id"]

    # ============== TRANSACTIONS ===============
    transactions = root.findall("./TRANSACTIONS/TRANSACTION")

    if "split_type" in vars():
        find_mismatches_in_slits(transactions, accounts, payees, split_type)

    if to_erase_number:
        erase_number(transactions, to_erase_number)

    if reconcile_flag is not None:
        fix_reconcile_flag(transactions, reconcile_flag)

    if "set_txn_numbers_flag" in vars():
        for account in root.findall("./ACCOUNTS/ACCOUNT[@parentaccount='AStd::Asset']"):
            assign_txn_numbers(root, account.get("id"))

    if "set_expenses_currency_flag" in vars():
        p = re.compile('^Expenses:')
        for account in root.findall("./ACCOUNTS/ACCOUNT"):
            acnt_name = traverse_account_hierarchy_backwards(accounts, account.get("id"))
            if p.match(acnt_name):
                account.set("currency", expenses_currency)

    if "to_add_default_tag" in vars():
        add_default_tag(transactions, accounts, tags, default_tag, excluded_tags)

    if "set_replace_tag_in_account_flag" in vars():
        # ============== REVERSE ACCOUNTS ===========
        rev_accounts = dict()
        for account in root.findall("./ACCOUNTS/ACCOUNT"):
            acnt_name = traverse_account_hierarchy_backwards(accounts, account.get("id"))
            rev_accounts[acnt_name] = account.get("id")

        target_acnt_key = list(filter(lambda x: replace_target_account in x, rev_accounts.keys()))[0]
        replace_target_acnt_id = rev_accounts[target_acnt_key]
        replace_tag_in_account(transactions, tags, replace_target_acnt_id, old_tag, new_tag)

    if "set_move_split_lvl_tag_to_txn_lvl" in vars():
        if tag_to_move in tags.keys():
            move_tag_from_split_level_to_txn_level(transactions, tags, tag_to_move, accounts)
        else:
            print(f"Tag {tag_to_move} was not found in the provided XML file.")

    if "to_reorder_tags" in vars():
        rev_tags = dict()
        for k in root.findall("./TAGS/TAG"):
            rev_tags[k.attrib["id"]] = k.attrib["name"]
        reorder_tags_in_txn(transactions, rev_tags)

    # ============== OUTPUT =====================
    xml_dmp = ET.tostring(root, encoding="utf8", xml_declaration=False)
    # Some symbol combinations need to be escaped or replaced
    rep_sym_dict = [
        ('" />', '"/>'),
        ("&gt;", ">"),
        ("&#10;", "&#xa;"),
        ("&#09;", "&#x9;"),
    ]
    # Replace a character array in 0st element of tuple with 1st element of tuple
    for k in rep_sym_dict:
        xml_dmp = xml_dmp.replace(bytes(k[0], "ascii"), bytes(k[1], "ascii"))

    # Convert bytes to string in UTF-8 encoding
    xml_dmp = xml_dmp.decode("utf8")

    # Divide badly formatted multiple nodes on the same line
    xml_dmp = xml_dmp.replace("><", ">\n<")

    with open(outputfile, "w", encoding="UTF-8") as f:
        doc_type = '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE KMYMONEY-FILE>\n'
        file = f"{doc_type}{xml_dmp}\n"
        f.write(file)
    return


if __name__ == "__main__":
    main(sys.argv)
