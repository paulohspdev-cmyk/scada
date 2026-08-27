using System.Text.Json;
using System.Xml;
using Scada.Client;

if (args.Length < 2)
{
    Console.Error.WriteLine("Uso: RcRapidReader <ScadaCommConfig.xml> <canal> [canal...]");
    return 2;
}

try
{
    string configFile = args[0];
    int[] cnlNums = args.Skip(1).Select(int.Parse).ToArray();

    XmlDocument xmlDoc = new XmlDocument();
    xmlDoc.Load(configFile);
    XmlNode connNode = xmlDoc.SelectSingleNode("/ScadaCommConfig/ConnectionOptions")
        ?? throw new Exception("ConnectionOptions não encontrado no ScadaCommConfig.xml");

    ConnectionOptions options = new ConnectionOptions();
    options.LoadFromXml(connNode);

    ScadaClient client = new ScadaClient(options);
    var data = client.GetCurrentData(cnlNums, false, out long listId);

    var channels = cnlNums.Select((cnl, i) => new
    {
        cnl,
        val = data[i].Val,
        stat = data[i].Stat,
        defined = data[i].IsDefined
    }).ToArray();

    Console.WriteLine(JsonSerializer.Serialize(new
    {
        ok = true,
        list_id = listId,
        channels
    }));
    return 0;
}
catch (Exception ex)
{
    Console.Error.WriteLine(JsonSerializer.Serialize(new
    {
        ok = false,
        error = ex.Message,
        type = ex.GetType().FullName
    }));
    return 1;
}
