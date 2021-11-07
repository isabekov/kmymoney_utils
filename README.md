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
    python3 kmymoney_utils.py [-enh] [-s <count>] [-r <flag>] [-o <outputfile>] <inputfile>.xml

Detailed help:

    python3 kmymoney_utils.py [-enh] [-s <count>] [-r <flag>] [-o <outputfile>] <inputfile>.xml

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
                                             <flag> can be equal to -1 (unknown) 0 (not reconciled), 1 (cleared),
                                             2 (reconciled) or 3 (frozen).
        -h --help                            Print this help message.
