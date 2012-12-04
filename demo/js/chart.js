var margin = {top: 30, right: 40, bottom: 40, left: 30},
	width = 500 - margin.left - margin.right,
	height = 400 - margin.top - margin.bottom;

var parseDate = d3.time.format("%Y-%m-%d").parse;

var color = d3.scale.category10();

ValueType = Backbone.Model.extend({
	defaults: {checked: true}
});

ValueTypes = Backbone.Collection.extend({
	model:ValueType
});

// Views
ValueTypeView = Backbone.View.extend({
	tagName: "li",
	events: {
		"click input": "change"
	},
	change: function(){
		this.model.set("checked", !this.model.get("checked"));
	},
	template: _.template($('#value_type_template').html()),
	render: function (eventName) {
        $(this.el).html(this.template(this.model.toJSON()));
        return this;
    }
});

ValueTypeListView = Backbone.View.extend({
    tagName:'ul',
    initialize:function () {
        this.model.bind("reset", this.render, this);
    },
    render:function (eventName) {
        _.each(this.model.models, function (vt) {
            $(this.el).append(new ValueTypeView({model:vt}).render().el);
            vt.bind("change", this.render_chart, this);
        }, this);
        return this;
    },
    render_chart: function(){
    	to_view = _.map(_.filter(this.model.models, function(m) {return m.get('checked')}), function(v) { return v.get("name")});
    	add_bar_chart("#workers_quality_"+this.dataset_name, 
    			"workers_quality_"+this.dataset_name+".csv",
    			this.dataset_name,
    			"Amount", "Worker quality", 0, to_view, false);
    }
});
 
var add_line_chart = function(place, datafile, y_axis_txt){
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

var add_multiline_chart = function(place, datafile1, datafile2, y_axis_txt){
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
	    .interpolate("basis")
	    .x(function(d) { return x(d.date); })
	    .y(function(d) { return y(d.temperature); });
	
	var svg = d3.select(place).append("svg")
	    .attr("width", width + margin.left + margin.right)
	    .attr("height", height + margin.top + margin.bottom)
	  .append("g")
	    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
	
	d3.tsv(datafile1, function(error, data) {
	  color.domain(d3.keys(data[0]).filter(function(key) { return key !== "date"; }));
	
	  data.forEach(function(d) {
	    d.date = parseDate(d.date);
	  });
	
	  var cities = color.domain().map(function(name) {
	    return {
	      name: name,
	      values: data.map(function(d) {
	        return {date: d.date, temperature: +d[name]};
	      })
	    };
	  });
	
	  x.domain(d3.extent(data, function(d) { return d.date; }));
	
	  y.domain([
	    d3.min(cities, function(c) { return d3.min(c.values, function(v) { return v.temperature; }); }),
	    d3.max(cities, function(c) { return d3.max(c.values, function(v) { return v.temperature; }); })
	  ]);
	
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
	
	  var city = svg.selectAll(".city")
	      .data(cities)
	    .enter().append("g")
	      .attr("class", "city");
	
	  city.append("path")
	      .attr("class", "line")
	      .attr("d", function(d) { return line(d.values); })
	      .style("stroke", function(d) { return color(d.name); });
	
	  city.append("text")
	      .datum(function(d) { return {name: d.name, value: d.values[d.values.length - 1]}; })
	      .attr("transform", function(d) { return "translate(" + x(d.value.date) + "," + y(d.value.temperature) + ")"; })
	      .attr("x", 3)
	      .attr("dy", ".35em")
	      .text(function(d) { return d.name; });
	});
}

var add_bar_chart = function(place, datafile, dataset_name, y_axis_txt, x_axis_txt, bar, to_view, render_checkboxes){
	var height = 300 - margin.top - margin.bottom;
	var x = d3.scale.ordinal()
	    .rangeRoundBands([0, width], .1);

	var y = d3.scale.linear()
	    .range([height, 0]);

	var xAxis = d3.svg.axis()
	    .scale(x)
	    .orient("bottom");

	var yAxis = d3.svg.axis()
	    .scale(y)
	    .orient("left");
	
	var line = d3.svg.line()
		.x(function(d) { return x(d.interval) + x.rangeBand()/2; })
		.y(function(d) { return y(d.value); });

	d3.select(place).html("");
	var svg = d3.select(place).append("svg")
	    .attr("width", width + margin.left + margin.right)
	    .attr("height", height + margin.top + margin.bottom)
	  .append("g")
	    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

	d3.tsv(datafile, function(error, data) {
		color.domain(d3.keys(data[0]).filter(function(key) { return key !== "interval"; }));
		
		var values = color.domain().map(function(name) {
			return {
				name: name,
				values: data.map(function(d) {
					return {interval: d.interval, value: +d[name]};
				})};
		});
		values = _.filter(values, function(v){
			return _.contains(to_view, v.name);
		});
		
		if (render_checkboxes){
			var vts = new ValueTypes();
			var vtsv = new ValueTypeListView({model: vts});
			vtsv.dataset_name = dataset_name;
			vts.add(values);
			$("#workers_quality_"+dataset_name+"_mode").html(vtsv.render().el);
		}
		
		x.domain(data.map(function(d) { return d.interval; }));
		y.domain([0, d3.max(values, function(c) { return d3.max(c.values, function(v) { return v.value; }); })]);

		svg.append("g")
			.attr("class", "x axis")
			.attr("transform", "translate(0," + height + ")")
			.call(xAxis)
		.append("text")
			.attr("x", width)
			.attr("dy", 30)
			.style("text-anchor", "end")
			.text(x_axis_txt);

		svg.append("g")
	      	.attr("class", "y axis")
	      	.call(yAxis)
	   	.append("text")
	   		.attr("transform", "rotate(-90)")
	   		.attr("y", 6)
	   		.attr("dy", ".71em")
	   		.style("text-anchor", "end")
	   		.text(y_axis_txt);

		function filter_func(element, index, array){
			return element.name !== bar;
		};
		//draw bar chart
		bar_vals = values.filter(function(element, index, array){
      		return !filter_func(element, index, array);
      	})[0];
		
		if (bar_vals && bar_vals.values.length){
			svg.selectAll(".bar")
			.data(bar_vals.values)
			.enter().append("rect")
			.attr("fill", function(d) { return color(bar_vals.name)})
			.attr("x", function(d) { return x(d.interval); })
			.attr("width", x.rangeBand())
			.attr("y", function(d) { return y(d.value); })
			.attr("height", function(d) { return height - y(d.value); });
		}
		
		//draw line charts
		var value_type = svg.selectAll(".city")
			.data(values.filter(filter_func))
			.enter().append("g")
			.attr("class", "city");
		value_type.append("path")
	      	.attr("class", "line")
	      	.attr("d", function(d) { return line(d.values); })
	      	.style("stroke", function(d) { return color(d.name); });
	
		value_type.append("text")
	      	.datum(function(d) { return {name: d.name, value: d.values[d.values.length - 1]}; })
	      	.attr("transform", function(d) { return "translate(" + x(d.value.interval) + "," + y(d.value.value) + ")"; })
	      	.attr("x", 3)
	      	.attr("dy", ".35em")
	      	.text(function(d) { return d.name; });
	});
}

add_multiline_chart("#label_fit_chart", "label_fit.csv", "Labels fitness (in %)");
add_multiline_chart("#time_chart", "time.csv", "Computation timing (in seconds)");

var datasets =['small', 'medium', 'big']; 
for (var t in datasets){
	d3.select("#workers_quality").append("h4").text(datasets[t] + " data set");
	d3.select("#workers_quality").append("div").attr("id", "workers_quality_"+datasets[t]);
	add_bar_chart("#workers_quality_"+datasets[t], 
			"workers_quality_"+datasets[t]+".csv",
			datasets[t], "Amount", "Worker quality", '', ['real', 'assumed'], true);
	d3.select("#workers_quality").append("div").attr("id", "workers_quality_"+datasets[t]+"_mode");
}
