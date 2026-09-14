from pycomm3 import LogixDriver

with LogixDriver("10.16.20.20") as plc:
    print(plc)
    print(plc.read("Run"))
    print(plc.info)
    resultado = plc.write(("QR_Code", "ABC123456"))