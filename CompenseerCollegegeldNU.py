import warnings
import time
import serial
import pandas as pd

# Connect to printer
printer = serial.Serial(port='COM7',
                        baudrate=19200)

# Read data, converted to csv for easy access
path = r'./data/CompensatieCollegegeld/petitie.csv'
length = 51272  # all names, however we just select 10%
# Convert to dataframe, select number of rows for testing
df = pd.read_csv(path, usecols=["Voornaam", "Achternaam"], nrows=int(
    length/10))  # Hard code number of rows to be 10%
# Convert names to full name
df["Full Name"] = df["Voornaam"] + ' ' + df["Achternaam"]
s = df.drop(["Voornaam", "Achternaam"], axis=1).squeeze()


def cut(prntr):
    '''
    Command to cut paper for bonnetje.

    param prntr: Serial printer instance.
    '''

    prntr.write(b'\033d0')


def write_text(prntr):
    """
    Write all text to bonnetje.

    param prntr: Serial printer instance.
    """

    # Print Primary Markup
    prntr.write("1/10\n".encode())
    prntr.write(f'{"        Compenseer Collegegeld NU!":>8}'.encode())
    prntr.write(b'\n\n\n\n')
    # Print Names
    EUR = '\200'
    for idx, name in s.items():
        strng = f"{str(name):<30}{f'{EUR}1000,-':>10}\n".encode()
        prntr.write(strng)
        # Pause 2 seconds once in a while to prevent overheating
        if idx % 500 == 0:
            time.sleep(5)

    prntr.write(b'\n\n')
    prntr.write(b'-' * 42)
    prntr.write(
        f"\nSUBTOTAAL:                   {EUR}{f'{len(s) * 1000},-':>10}\n".encode())
    prntr.write(b'\n\n')
    prntr.write(
        f"\nTOTAAL (x10):                {EUR}{f'{length * 1000},-':>10}\n".encode())
    prntr.write(b'\n\n')
    # Print Final Markup
    prntr.write(b'\n\n\n\n\n\n\n\n')
    prntr.write(b'Made by: Micha van den Herik; @kliklaminaat')
    prntr.write(b'\n\n\n\n\n\n\n\n')
    cut(printer)


# Run Program
write_text(printer)
