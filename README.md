# Utilities for batch editing a KMyMoney's XML file

This script processes transactions listed in a KMyMoney's XML file and modifies certains attributes in a batch mode.

Features:

  - fixing mismatching splits in transactions of KMyMoney's XML file,
  - erasing/setting "number" inside a split in a transaction in batch mode,
  - overwrite reconcile flag in all splits in all transactions.

Read the article ["Structure of a KMyMoney XML File"](https://www.isabekov.pro/structure-of-a-kmymoney-xml-file/) to
better understand the file format.


## Use
Decompress gzipped *.kmy file first and then run the script:

    cat [inputfile].kmy | gunzip > [inputfile].xml
    python3 kmymoney_utils.py [options/flags] [-o <outputfile>] <inputfile>.xml

Detailed help:

    python3 ./kmymoney_utils.py [options/flags] [-o <outputfile>] <inputfile>.xml

    Input arguments:
        -o --output                          Output file, if not specified, output file is set to
                                             "<input file>_fixed.xml". Input file should always be a KMyMoney XML file.
        -e --erase-txn-numbers               Erase all transaction numbers (i.e. "number" attribute in a split).
        -n --assign-txn-numbers              Assign integer values to all transactions in an account
                                             sorted in chronological order by "post date". The earliest transaction
                                             is assigned number 1, the ones following it will have numbers incremented
                                             by one. Iterate over all asset accounts.
        -s --fix-splits-with-count <count>   If <count> is 2, then fix empty payee for the second split in a transaction
                                             with 2 splits by assigning the payee from the first split.
                                             If <count> is 1, then display transactions with a single split.
                                             In a double-entry accounting system, there have to be two splits in a
                                             transaction for the consistency purpose.
                                             Usually, payees in a transaction with 2 splits should be identical.
                                             Transactions with 1 split should be checked manually, because
                                             even for opening balances the money is transferred from an equity account,
                                             which means the 2nd split must exist and contain equity account information.
        -r --reconcile-flag  <flag>          Assign reconcile <flag> to all splits in all transactions.
                                             <flag> can be equal to -1 (unknown), 0 (not reconciled), 1 (cleared),
                                             2 (reconciled) or 3 (frozen).
        -a --add-tag-if-not-tagged <tag>     Add default tag if it is not present at split/transaction.
                                             under condition that split/condition is not associated with tags in "-x"
                                             option (default tag and excluded tags are mutually exclusive).
        -x --excluded-tags <tag1>,<tag2>     List of exluded tags separated by a comma.
                                             Arguments "-a household_1 -x household_2,household_3" will add default tag
                                             "household_1" to a split/transaction if it is not taged by tags
                                             "household_2" and "household_3".
        -d --replace-tag-with <foo>,<bar>    Replace tag <foo> with tag <bar> in account specified by "--in-account".
        -i --in-account <acnt>               Target account whose transactions(-splits) will have tags replaced.
                                             Arguments '-i "ExtraHousehold" -d household_1,household_2' will replace
                                             tag "household_1" with tag "household_2" for transactions in account
                                             "ExtraHousehold". Account name should a substring of the full account name.
        -m --move-split-lvl-tag-to-txn-lvl   Move tag from split level to transaction level if all splits in a the
                                             transaction have this tag assigned. Erase the tag at split level.
        -c --set-expenses-currency <curr>    Set all expense accounts' currency to <curr>.
        -h --help                            Print this help message.

