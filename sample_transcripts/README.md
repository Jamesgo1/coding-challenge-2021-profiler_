# Member Desconstructor for NI Assembly Hansard Minutes

## Quick start

This is an example of a Lintol processor. You can run it like so:

    ltldoorstep -o html --output-file output.html process None profile_processor.py -e dask.threaded

This will create output.html in the current directory and, in a browser (tested with Chrome).

Unfortunately, custom date ranges, identifiers, and outputs have not been implemented for the command line. However, to
run this locally:

~~~
import profile_processor_with_imports

profile_analyzer = profile_processor_with_imports.ProfileAnalyzer()
profile_analyzer.get_identifiers("gender")
profile_analyzer.get_output_analytics("word_count")
profile_analyzer.get_date_range(start_date="2020-01-01", end_date="2021-01-01")
analysis_output_dict = profile_analyzer.run_profile_analysis()
~~~

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
options. Unfortunately, this is a topic I'm not very experienced in, so was not sure exactly how to implement this.

Additionally, this processor has focused heavily on the grunt work of getting the data into a workable format. It is my
hope that this foundation can allow for the more illuminating side of data analysis. It would be interesting to take the
data from this processor and visualize trends over time - such as the changing levels of semantic subjectivity.

## Notes

A fair bit less was implemented than hoped. Unfortunately, my ideas are a lot greater than my time.

Please see TODOs for details in the code.

To summarize feautres I planned to add:

- Add highlighting of desired analytic (e.g. highlight all instances of the DUP being interrupted)
- Add commandline options (date, identifiers, analytics)
- Add data visualization.
- Testing. Sorry Kent Beck.