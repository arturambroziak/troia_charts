var add_new_chart = function(place, datafile, y_axis_txt){

	var margin = {top: 30, right: 30, bottom: 30, left: 30},
			    width = 480 - margin.left - margin.right,
			    height = 250 - margin.top - margin.bottom;
			
	var parseDate = d3.time.format("%Y-%m-%d").parse;
	
	var x = d3.time.scale()
	    .range([0, width]);
	
	var y = d3.scale.linear()
	    .range([height, 0]);
	
	var xAxis = d3.svg.axis()
	    .scale(x)
	    .orient("bottom");
	
	var yAxis = d3.svg.axis()
	    .scale(y)
	    .orient("left");
	
	var line = d3.svg.line()
	    .x(function(d) { return x(d.date); })
	    .y(function(d) { return y(d.value); });
	
	var svg = d3.select(place).append("svg")
	    .attr("width", width + margin.left + margin.right)
	    .attr("height", height + margin.top + margin.bottom)
	  .append("g")
	    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
	
	d3.tsv(datafile, function(error, data) {
	  data.forEach(function(d) {
	    d.date = parseDate(d.date);
	    d.value = +d.value;
	  });
	
	  x.domain(d3.extent(data, function(d) { return d.date; }));
	  y.domain(d3.extent(data, function(d) { return d.value; }));
	
	  svg.append("g")
	      .attr("class", "x axis")
	      .attr("transform", "translate(0," + height + ")")
	      .call(xAxis);
	
	  svg.append("g")
	      .attr("class", "y axis")
	      .call(yAxis)
	    .append("text")
	      .attr("transform", "rotate(-90)")
	      .attr("y", 6)
	      .attr("dy", ".71em")
	      .style("text-anchor", "end")
	      .text(y_axis_txt);
	
	  svg.append("path")
	      .datum(data)
	      .attr("class", "line")
	      .attr("d", line);
	});
};

add_new_chart("#label_fit_chart", "label_fit.csv", "Labels fitness (in %)");
add_new_chart("#time_chart", "time.csv", "Comptation timing (in seconds)");
