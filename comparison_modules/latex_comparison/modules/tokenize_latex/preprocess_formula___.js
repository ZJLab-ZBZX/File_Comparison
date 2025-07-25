const katex = require('katex');
//var path = require('path');
//var options = require(path.join(__dirname,"node_modules/katex/src/Options.js"))
var readline = require('readline');
var rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
});


rl.on('line', function(line){
    //a = line
    //if (line[0] == "%") {
    //    line = line.substr(1, line.length - 1);
    //}
    //line = line.split('%')[0];

    //line = line.split('\\~').join(' ');
    
    //for (var i = 0; i < 300; i++) {
    //    line = line.replace(/\\>/, " ");
    //    line = line.replace('$', ' ');
    //    line = line.replace(/\\label{.*?}/, "");
    //}

    //if (line.indexOf("matrix") == -1 && line.indexOf("cases")==-1 &&
    //    line.indexOf("array")==-1 && line.indexOf("begin")==-1)  {
    //    for (var i = 0; i < 300; i++) {
    //        line = line.replace(/\\\\/, "\\,");
    //    }
    //}
    

    line = line + " "
    // global_str is tokenized version (build in parser.js)
    // norm_str is normalized version build by renderer below.
    try {
    
        if (process.argv[2] == "tokenize") {
            var tree = katex.__parse(line, {});
            console.log(global_str.replace(/\\label { .*? }/, ""));
        } else {
			//var html = katex.renderToString("\\begin{align} c = \\pm\\sqrt{a^2 + b^2}\\end{align}", {throwOnError: false, displayMode: true});
			//console.log('html');
			//console.log(html);
            //for (var i = 0; i < 300; ++i) {
            //    line = line.replace(/{\\rm/, "\\mathrm{");
            //    line = line.replace(/{ \\rm/, "\\mathrm{");
            //    line = line.replace(/\\rm{/, "\\mathrm{");
            //}

            var tree = katex.__parse(line, {displayMode: true});
            //var tree = katex.__parse("\\int_{\\phantom{a}b}^c f(x) \\, dx \\quad \\text{vs} \\quad \\int_{a}^b f(x) \\, dx", {displayMode: true});
            //console.log('tree', tree)
            //console.log(tree[0]['body'][0][0]['body'][0])
            buildExpression(tree, {});            
            //for (var i = 0; i < 300; ++i) {
            //    norm_str = norm_str.replace('SSSSSS', '$');
            //    norm_str = norm_str.replace(' S S S S S S', '$');
            //}
			norm_str = norm_str.replace(/\\mathrel { \\mathrel { \\mathrlap { \\not } } = }/g, '\\neq');
            norm_str = norm_str.replace(/\\varvdots/g, "\\vdots")
			norm_str = norm_str.replace(/@/g, '');
			//console.log(line);
			//console.log('\n')
			console.log(norm_str);
            //console.log(norm_str.replace(/\\label { .*? }/, ""));
        }
    } catch (e) {
        console.log('line:\n', line);
		console.log();
        console.log('norm_str:\n', norm_str);
        console.error(e);
		console.error(line);
        //console.log();
    }
    global_str = ""
    norm_str = ""
})



// This is a LaTeX AST to LaTeX Renderer (modified version of KaTeX AST-> MathML).
norm_str = ""

var groupTypes = {};

groupTypes.mathord = function(group, options) {
	if (group.mode == 'text') {
		norm_str = norm_str + group.text;
	} else {
		norm_str = norm_str + group.text + " ";
	}
    //if (false){//(options.font == "mathrm"){
    //    for (i = 0; i < group.value.length; ++i ) {
    //        if (group.value[i] == " ") {
    //            norm_str = norm_str + group.text[i] + "\; ";
    //        } else {
    //            norm_str = norm_str + group.text[i] + " ";
    //        }
    //    }
    //} else {
    //    norm_str = norm_str + group.text + " ";
    //}
};

groupTypes.atom = function(group, options) {
    norm_str = norm_str + group.text + " ";
};

groupTypes.textord = function(group, options) {
	//这里可以加个options控制选项如果父节点是text则不加空格，否则加空格，mathpix好像是这样的
	if (group.mode == 'text') {
		norm_str = norm_str + group.text;
	} else {
		norm_str = norm_str + group.text + " ";
	}
	
	//原版本会让\text{}里的空格越来越长，尤其是多次normalize
    //norm_str = norm_str + group.text + " ";
};

groupTypes.bin = function(group) {
    norm_str = norm_str + group.value + " ";
};

//groupTypes.rel = function(group) {
//    norm_str = norm_str + group.value + " ";
//}; //=

//groupTypes.open = function(group) {
//    norm_str = norm_str + group.value + " ";
//}; //(

//groupTypes.close = function(group) {
//    norm_str = norm_str + group.value + " ";
//}; //)

groupTypes.inner = function(group) {
    norm_str = norm_str + group.value + " ";
};

groupTypes.punct = function(group) {
    norm_str = norm_str + group.value + " ";
};

groupTypes.ordgroup = function(group, options) {
	//console.log('here', group.body.length == 1 && group.body[0].type=='ordgroup')
	//console.log(group.body);
	if (group.body.length == 1 && group.body[0].type=='ordgroup') {
		buildGroup(group.body[0], options);
	} else {
		//即使{}内为空也得渲染否则可能和原始结构不一致，例如空分母
		if (group.mode == 'text') {
			norm_str = norm_str + "{";     
            buildExpression(group.body, options);
            norm_str = norm_str +  "}";
		}
		else {
			norm_str = norm_str + "{ ";     
            buildExpression(group.body, options)
            norm_str = norm_str +  "} ";
			}
		//if (group.body.length) {
        //    norm_str = norm_str + "{ ";

        //    buildExpression(group.body, options);

        //    norm_str = norm_str +  "} ";
	    //}
	}
};

groupTypes.text = function(group, options) {
    
    norm_str = norm_str + group.font + " {"; //括号内不加空格

    buildExpression(group.body, options);
    norm_str = norm_str + "} ";
};

groupTypes.kern = function(group, options) {
	if (group.dimension.unit == 'mu') {
        norm_str = norm_str + "\\mkern " + group.dimension.number + 'mu ';
	} else if (group.dimension.unit == 'em') {
		norm_str = norm_str + "\\mkern " + group.dimension.number * 18 + 'mu ';
	}
	else {
		throw "Got unknown unit '" + group.dimension.unit + "'";
	}
};

groupTypes.color = function(group, options) {
    var inner = buildExpression(group.body, options);

    //var node = new mathMLTree.MathNode("mstyle", inner);

    //node.setAttribute("mathcolor", group.value.color);

    //return node;
};

groupTypes.supsub = function(group, options) {
	//console.log(group);
	if (group.base !== null) {
		buildGroup(group.base, options);
	}
    
    if (group.sub) {
        norm_str = norm_str + "_ ";
        if (group.sub.type != 'ordgroup') {
            norm_str = norm_str + "{ ";
            buildGroup(group.sub, options);
            norm_str = norm_str + "} ";
        } else {
            buildGroup(group.sub, options);
        }
        
    }

    if (group.sup) {
        norm_str = norm_str + "^ ";
        if (group.sup.type != 'ordgroup') {
            norm_str = norm_str + "{ ";
            buildGroup(group.sup, options);
            norm_str = norm_str + "} ";
        } else {
            buildGroup(group.sup, options);
        }
    }

};

groupTypes.genfrac = function(group, options) {
	//console.log(group);
    if (!group.hasBarLine) {
        norm_str = norm_str + "\\binom ";
    } else {
        norm_str = norm_str + "\\frac ";
    }
    buildGroup(group.numer, options);
    buildGroup(group.denom, options);

};

groupTypes.array = function(group, options) {
    //console.log(group);
    norm_str = norm_str + "\\begin{array} { ";
	//console.log(group.body[0]);
	//console.log(group.body[0][0].body[0]);
    //console.log(group.body[0][1].body[0]);
	//console.log(group.body[0][2].body[0]);
	//ccc
    if (group.cols) {
        group.cols.map(function(start) {
            if (start && start.align) {
                norm_str = norm_str + start.align + " ";
			} else if (start && start.separator) {
				norm_str = norm_str + start.separator + " ";
			}
		} );
    } else {
        group.body[0].map(function(start) {
            norm_str = norm_str + "l ";
        } );
    }
    norm_str = norm_str + "} ";
    group.body.map(function(row) {
        if (row.some(cell => cell.body.length > 0)) { // orginal code: if (row[0].value.length > 0)
            out = row.map(function(cell) {
                buildGroup(cell, options);
                if (norm_str.length > 4 
                    && norm_str.substring(norm_str.length-4, norm_str.length) == "{ } ") {
                    norm_str = norm_str.substring(0, norm_str.length-4) ;
                }
                norm_str = norm_str + "& ";
            });
            norm_str = norm_str.substring(0, norm_str.length-2) + "\\\\ ";
        }
    }); 
    norm_str = norm_str + "\\end{array} ";
};

groupTypes.sqrt = function(group, options) {
    var node;
    if (group.index) {
        norm_str = norm_str + "\\sqrt [ ";
        buildExpression(group.index.body, options);
        norm_str = norm_str + "] ";
        buildGroup(group.body, options);
    } else {
        norm_str = norm_str + "\\sqrt ";
        buildGroup(group.body, options);
    }
};

groupTypes.leftright = function(group, options) {

    norm_str = norm_str + "\\left" + group.left + " ";
    buildExpression(group.body, options);
    norm_str = norm_str + "\\right" + group.right + " ";
};

groupTypes.accent = function(group, options) {
	//console.log('group', group);
    if (group.base.type != 'ordgroup') {
        norm_str = norm_str + group.label + " { ";
        buildGroup(group.base, options);
        norm_str = norm_str + "} ";
    } else {
        norm_str = norm_str + group.label + " ";
        buildGroup(group.base, options);
    }
};

groupTypes.spacing = function(group) {
	if (group.mode == 'text') {
		norm_str = norm_str + group.text;
	} else {
		norm_str = norm_str + group.text + " ";
	}
	//norm_str = norm_str + group.text;
    //原版本会让\text{}里的空格越来越长，尤其是多次normalize
	//var node;
    //if (group.text == " ") {
    //    norm_str = norm_str + "~ ";
    //} else {
    //    norm_str = norm_str + group.text + " ";
    //}
    //return node;
};

groupTypes.op = function(group, options) {
    var node;

    // TODO(emily): handle big operators using the `largeop` attribute
    
    //console.log('group', group);
    if (group.symbol) {
        // This is a symbol. Just add the symbol.
        norm_str = norm_str + group.name + " ";
		if (group.alwaysHandleSupSub == true) {
			norm_str = norm_str + "\\limits ";
		}

    } else {
        //if (group.limits == false) {
		if (group.alwaysHandleSupSub == false) {
            norm_str = norm_str + "\\operatorname { "; //这里三个反斜杠被改成两个，不一定对
        } else {
            norm_str = norm_str + "\\operatorname* { ";
        }
		if (group.body) {
			buildExpression(group.body, options);
		} else {
			for (i = 1; i < group.name.length; ++i ) {
				norm_str = norm_str + group.name[i] + " ";
            }
		}
        norm_str = norm_str + "} ";
		if (group.alwaysHandleSupSub == true) {
			norm_str = norm_str + "\\limits ";
		}
    }
};

groupTypes.operatorname = function(group, options) {
    //console.log(group);
    //if (group.limits == false) {
	if (group.alwaysHandleSupSub == false) {
        norm_str = norm_str + "\\operatorname { ";   //这个节点是自己写的，参考op的代码，三个反斜杠改成两个
    } else {
        norm_str = norm_str + "\\operatorname* { ";
    }
    buildExpression(group.body, options);
    norm_str = norm_str + "} ";
	if (group.alwaysHandleSupSub == true) {
		norm_str = norm_str + "\\limits ";
	}
};

groupTypes.htmlmathml = function(group, options) {
    //console.log(group);
	const original = norm_str;
    buildExpression(group.html, options);
	const growthPart = norm_str.slice(original.length);
    norm_str = original + growthPart.replace(/@/g, '');
    //console.log(growthPart);
};

groupTypes.mclass = function(group, options) {
	//console.log(group);
	//if (group.mclass == 'mrel') {
	//	norm_str = norm_str + "\\mathrel { ";
	//	buildExpression(group.body, options);
	//	norm_str = norm_str + "} ";
	//} else if (group.mclass == 'mord') {
	//	norm_str = norm_str + "\\mathord { ";
	//	buildExpression(group.body, options);
	//	norm_str = norm_str + "} ";
	//} else {
	//	throw new katex.ParseError(
    //        "Got unknown mclass: '" + group.mclass + "'");
	//}
    norm_str = norm_str + "\\math" 
	for (i = 1; i < group.mclass.length; ++i ) {
			norm_str = norm_str + group.mclass[i];
        }
	norm_str = norm_str + " { ";
	buildExpression(group.body, options);
	norm_str = norm_str + "} ";
	
};

groupTypes.horizBrace = function(group, options) {
	//参考了accent的写法，当base不是{}时加上{}
    if (group.base.type != 'ordgroup') {
        norm_str = norm_str + group.label + " { ";
        buildGroup(group.base, options);
        norm_str = norm_str + "} ";
    } else {
        norm_str = norm_str + group.label + " ";
        buildGroup(group.base, options);
    }
};

groupTypes.mathchoice = function(group, options) {
	//console.log(group);
	//不确定是display还是text还是其他
    if ('display' in group && group.display !== undefined) {
        buildExpression(group.display, options);
    } else {
		console.log(group);
        throw "Got unknown mathchoice.";
    }
};

groupTypes.xArrow = function(group) {
	//console.log(group);
	norm_str = norm_str + group.label;
	buildGroup(group.body);

};

groupTypes.smash = function(group) {
	//console.log(group);
	norm_str = norm_str + '\\smash';
	buildGroup(group.body);

};

groupTypes.internal = function(group) {
    //这个节点还不清楚
    norm_str = norm_str + " ";
};

groupTypes.pmb = function(group) {
	//console.log(group);
	if (group.mclass == 'mord' | group.mclass == 'mrel') {
		norm_str = norm_str + "\\pmb { ";
		buildExpression(group.body);
		norm_str = norm_str + "} "
	} else {
		throw "pmb unknown mclass."
	}
};

groupTypes.enclose = function(group, options) {
	var label = group.label;
	if (label == '\\fbox') {
		label = '\\boxed'
	} else {
		throw "unknown enclose label"
	}
	//console.log(group);
    norm_str = norm_str + label + " ";
    buildGroup(group.body, options);
};

groupTypes.middle = function(group, options) {
	norm_str = norm_str + '\\middle ' + group.delim + ' ';
	
};

//groupTypes.katex = function(group) {
//    var node = new mathMLTree.MathNode(
//        "mtext", [new mathMLTree.TextNode("KaTeX")]);

//   return node;
//};


groupTypes.font = function(group, options) {
	//console.log(group);
	//console.log(group.body);
    var font = group.font;
    if (font == "mbox" || font == "hbox") {
        font = "mathrm";
    }
	norm_str = norm_str + "\\" + font + " ";
	if (group.body.type != 'ordgroup') {
        norm_str = norm_str + "{ ";
        buildGroup(group.body, options);
        norm_str = norm_str + "} ";
    } else {
        buildGroup(group.body, options);
    }
};

groupTypes.delimsizing = function(group) {
	//console.log(group);
    var children = [];
    //norm_str = norm_str + group.value.funcName + " " + group.value.value + " ";
	norm_str = norm_str + group.delim + " ";
};

groupTypes.styling = function(group, options) {
	//console.log(group);
    //norm_str = norm_str + " " + group.value.original + " ";
    norm_str = norm_str + '\\' + group.style + 'style' + ' ';
    buildExpression(group.body, options);

};

groupTypes.sizing = function(group, options) {
    const font_sizes = [
        'tiny', 'scriptsize', 'scriptsize', 'footnotesize', 'small', 'normalsize', 
        'large', 'Large', 'LARGE', 'huge', 'Huge'
        ]
    if (false) { //(group.value.original == "\\rm") {
        norm_str = norm_str + "\\mathrm { "; 
        buildExpression(group.value.value, options.withFont("mathrm"));
        norm_str = norm_str + "} ";
    } else {
        norm_str = norm_str + " " + "\\" + font_sizes[group.size-1] + " ";
        buildExpression(group.body, options);
    }
};

groupTypes.overline = function(group, options) {
	// overline、underline的body本来就是ordergroup
	//console.log(group);
	norm_str = norm_str + "\\overline "
    //norm_str = norm_str + "\\overline { ";
    
    buildGroup(group.body, options);
    //norm_str = norm_str + "} ";

};

groupTypes.underline = function(group, options) {
	norm_str = norm_str + "\\underline "
    //norm_str = norm_str + "\\underline { ";
    buildGroup(group.body, options);
    //norm_str = norm_str + "} ";


};

groupTypes.rule = function(group) {
    norm_str = norm_str + "\\rule { "+group.width.number+" "+group.width.unit+"  } { "+group.height.number+" "+group.height.unit+ " } ";

};

groupTypes.lap = function(group, options) {
    norm_str = norm_str + '\\math' + group.alignment + ' ';
    buildGroup(group.body, options);
};

//groupTypes.llap = function(group, options) {
//    norm_str = norm_str + "\\llap ";
//    buildGroup(group.value.body, options);
//};

//groupTypes.rlap = function(group, options) {
//    norm_str = norm_str + "\\rlap ";
//    buildGroup(group.value.body, options);
//};


groupTypes.vphantom = function(group, options, prev) {
    //norm_str = norm_str + "\\vphantom { ";
    //buildExpression(group.body, options);
    //norm_str = norm_str + "} ";
	norm_str = norm_str + "\\vphantom ";
	buildGroup(group.body, options);
};

groupTypes.hphantom = function(group, options, prev) {
    //norm_str = norm_str + "\\vphantom { ";
    //buildExpression(group.body, options);
    //norm_str = norm_str + "} ";
	norm_str = norm_str + "\\hphantom ";
	buildGroup(group.body, options);
};


groupTypes.phantom = function(group, options, prev) {
    norm_str = norm_str + "\\phantom { ";
    buildExpression(group.body, options);
    norm_str = norm_str + "} ";

};

/**
 * Takes a list of nodes, builds them, and returns a list of the generated
 * MathML nodes. A little simpler than the HTML version because we don't do any
 * previous-node handling.
 */
var buildExpression = function(expression, options) {
    var groups = [];
    for (var i = 0; i < expression.length; i++) {
        var group = expression[i];
        buildGroup(group, options);
    }
    // console.log(norm_str);
    // return groups;
};

/**
 * Takes a group from the parser and calls the appropriate groupTypes function
 * on it to produce a MathML node.
 */
var buildGroup = function(group, options) {
	//console.log(group);
    if (groupTypes[group.type]) {
        //console.log('group', group);
        groupTypes[group.type](group, options);
    } else {    
        console.log('group:', group);
		console.log(group.body.body[0]);
		//console.log('group.text', group.text);
		//console.log('group.display', group.text);
		//console.log('group.body[0]:', group.body[0], 'group.body[0].html:', group.body[0].html, 'group.body[0].html[0].body:',group.body[0].html[0].body, ' group.body[0].html[0].body[0].body:', group.body[0].html[0].body[0].body);
		//console.log(group.body[0].mathml, group.body[0].mathml[0].text);
        throw "Got group of unknown type: '" + group.type + "'";
    }
};


