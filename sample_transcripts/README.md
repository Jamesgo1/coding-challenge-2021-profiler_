# Member Desconstructor for NI Assembly Hansard Minutes

## Quick start

This is an example of a Lintol processor. You can run it like so:

    python3 processor.py out-example-2021-02-01-hansard-plenary.txt

or, if you would like a nicely-formatted HTML page to look at:

    ltldoorstep -o html --output-file output.html process sample_transcripts/out-example-2021-02-01-hansard-plenary.txt processor.py -e dask.threaded

This will create output.html in the current directory and, in a browser (tested with Chrome), should look like
output.png.

## What does it do?

The Member Deconstructor processor provides different lenses from which to analyse how MLAs engage within the Assembly
Chamber depedning on their profile. It provides a number of classes which allow you to easily build a customized dataset
according to the type of inight you wish to find.

It can help to answer questions such as:
> Do men speak more proportionally than women in the Chamber?

Likewise, it can prompt investigative questions such as:
> Why did Members of *X Party* ask more questions than those of *Y Party* during *Z* dates?

The customized timeframe also allows for specific questions such as:
> Do women proportionally speak more in 2021 than they did in 2016?

## Output and Input Options

This processor allows you to input one or more *identifier profiles*
and find out how they compare based on a number of *output measures*. There is total flexibility when it comes to which
profile options are chosen and which measures to analyze. None of the input or output variables are dependent on one
another.

<table>
<tr>
<th>Identiifer Profile Options</th>
<th>Output Comparison Options</th>
</tr>
<tr>
<td>
<li>Gender</li>
<li>Political party</li>
<li>Proximity to Stormont</li>
<li>Constituency</li>
</td>
<td>
<li>Number of words spoken</li>
<li>Number of interruptions</li>
<li>Polarity of words spoken</li>
<li>Subjectivity of words spoken</li>
</td>
</tr>
</table>

## Extendability

The processor is highly extendable. The only limits to adding new profile options is data availability. If data is
available and the profile option is interesting, it can be added easily.

Likewise, a new comparison output can be created and appended to the pipeline which could provide benefits to previously
created profile options.

## Limitations and Areas of Improvement

This project as it stands has areas where it could be greatly improved. Most prominently is with scalability when it
comes to larger timeframes and therefore bigger datasets. Plainly, it's too slow. Due to the large amount of iterating
loops, the processing becomes exponentially expensive rather than in a more linear fashion.

There are clear opportunities for parallelization, particularly when it comes to iterating through different profile
options.

Additionally, this processor has focused heavily on the grunt work of getting the data into a workable format. It is my
hope that this foundation can allow for the more illuminating side of data analysis. It would be interesting to take the
data from this processor and visualize trends over time - such as the changing levels of semantic subjectivity.

## Notes

You do not have to use Python, or a specific version of Python, _provided_ that your code takes in and outputs the
correct reporting schemas. The easiest way to ensure this is to use the Python ltldoorstep libraries as shown here (it
handles that automatically for you).

You are welcome to add additional open source dependencies to the requirements.txt, or additional open data to add extra
reports. While we do not expressly prohibit calling out to external services, solutions that run without hitting
third-party APIs may be seen more favourably.
