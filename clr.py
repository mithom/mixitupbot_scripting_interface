import re
import dotnet

splitter = re.compile('/{1,2}|\\{1,2}')

# noinspection PyPep8Naming
def AddReference(ref):
    if isinstance(ref, str)and not ref.startswith('IronPython'):
        dotnet.add_assemblies(ref)
        dotnet.load_assembly(splitter.split(ref)[-1][:-4])