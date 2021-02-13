This data is available via the NI Assembly's Open Data portal.

From the (http://data.niassembly.gov.uk/)[http://data.niassembly.gov.uk/] website:

> How can I use this data?
> The data and information available through data.niassembly.gov.uk are available under terms described in the Open Government Licence.
>
> You are free to:
>
> copy, publish, distribute and transmit the Information;
> adapt the Information;
> exploit the Information commercially and non-commercially for example, by combining it with other Information, or by including it in your own product or application.
> You must, where you do any of the above:
>
> acknowledge the source of the information in your product or application by including the following attribution statement and, where possible, provide a link to this licence: Contains Parliamentary information licensed under the Open Government Licence v3.0

Example for retrieving data from the NI Assembly Hansard web service:

    curl 'http://data.niassembly.gov.uk/hansard.asmx/GetHansardComponentsByPlenaryDate' --data-raw 'plenaryDate=2021-02-01T00%3A00%3A00%2B00%3A00'

Please note that GDPR provisions may still apply to open data, if it contains personally identifiable information.
