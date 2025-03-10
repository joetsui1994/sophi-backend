#!/usr/bin/env node

import * as d3 from 'd3';
import fs from 'fs';
import _yargs from 'yargs';
import { hideBin } from 'yargs/helpers';
const yargs = _yargs(hideBin(process.argv));

const options = yargs
    .usage("Usage: -i <tree_json> -o <output_json>")
    .option("i", { alias: "tree", describe: "input tree in json format", type: "string", demandOption: true })
    .option("h", { alias: "height", describe: "target tree height", type: "number", demandOption: false, default: 1000 })
    .option("w", { alias: "width", describe: "target tree width", type: "number", demandOption: false, default: 1000 })
    .argv;

function visit(parent, childrenFn) {
    if (!parent) return;
    var children = childrenFn(parent);
    if (children) {
        children.forEach(child => visit(child, childrenFn));
    }
}
    
function setLayerCount(source) {
    var levelWidth = [1];

    var childCount = function(level, n) {
        n.layerCount = 0;
        if (n.data.type == "node") {
            if (levelWidth.length <= level + 1) levelWidth.push(0);
            var children = n.children || n._children;
            levelWidth[level + 1] += children.length;

            children.forEach(function(d) {
                n.layerCount = Math.max(n.layerCount, 1 + childCount(level + 1, d));
            });
            return n.layerCount;
        } else {
            return 0;
        };
    };
    source.layerCount = childCount(0, source);
    source.maxDepth = levelWidth.length - 1;
}

function setMaxBranchLength(source) {
    var getMaxBranchLength = function(n) {
        if (n.data.type == "node") {
            var branchLength = parseFloat(n.data.brlen) || 0;
            var maxChildBranchLength = 0;
            var children = n.children || n._children;
            children.forEach(function(d) {
                maxChildBranchLength = Math.max(maxChildBranchLength, getMaxBranchLength(d));
            });
            return branchLength + maxChildBranchLength;
        } else {
            return parseFloat(n.data.brlen) || 0;
        }
    }
    source.maxBranchLength = getMaxBranchLength(source);
}

function sortNodes(source) {
    var _sortNodes = function(n) {
        if (n.data.type == "node") {
            var children = n.children || n._children;
            children.sort((a,b) => {
                if (a.data.type == "node" || b.data.type == "node") {
                    return a.layerCount - b.layerCount;
                } else {
                    return b.data.name.toLowerCase() < a.data.name.toLowerCase() ? 1 : -1;
                };
            });
            children.forEach(d => _sortNodes(d));
        };
    };
    _sortNodes(source);
}

function setOrder(source) {
    var order = 0;
    source.minOrder = 0;
    var _setOrder = function(n) {
        if (n.data.type == "node") {
            var children = n.children || n._children;
            children.forEach(function(d) {
                d.minOrder = order + 1;
                _setOrder(d);
                d.maxOrder = order;
            });
        } else {
            order += 1;
            n.order = order;
        };
    };
    _setOrder(source);
    source.leafNodeCount = order;
    source.maxOrder = order;
}

function setXY(source) {
    var nodeXY = [];
    var xStep = options.height / source.leafNodeCount;
	var yStep = options.width / source.maxBranchLength;

    var _setXY = function(n, brlen) {
        if (!(n.data.type == "node")) {
            n.y = brlen + (parseFloat(n.data.brlen) || 0) * yStep;
            n.x = n.displayOrder * xStep;
        } else {
            var xSum = 0;
            var nodeCount = 0;
            var children = n.children || n._children;
            n.y = brlen + (parseFloat(n.data.brlen) || 0) * yStep;
            children.forEach(function(d){
                _setXY(d, n.y);
                xSum += d.x;
                nodeCount += 1;
            });
            n.x = xSum / (n.children ? nodeCount : 2);
        };
        nodeXY.push({ 'name': n.data.name, 'x': n.x, 'y': n.y, ...n.data })
    };
    _setXY(source, 0);

    return nodeXY;
}

function setMaxX(source) {
    var _setMaxX = function(n) {
        if (!(n.data.type == "node")) {
            n.maxX = n.x;
            n.minX = n.x;
        } else {
            n.maxX = 0;
            n.minX = Infinity;
            var children = n.children || n._children;
            children.forEach(function(d){
                _setMaxX(d);
                n.maxX = Math.max(n.maxX, d.maxX);
                n.minX = Math.min(n.minX, d.minX);
            });
        }
    }
    _setMaxX(source);
}

function setDisplayOrder(source) {
    var displayOrder = 0;
    var _setDisplayOrder = function(n) {
        if (n.data.type == "node") {
            var children = n.children || n._children;
            children.forEach(d => _setDisplayOrder(d));
        } else {
            displayOrder += 1;
            n.displayOrder = displayOrder;
        };
    }
    _setDisplayOrder(source);
}

fs.readFile(options.tree, (err, data) => {
    if (err) {
        console.error(err);
        process.exit(1);
    }
    var treeData = JSON.parse(data);

    d3.tree().size([options.height, options.width]);
	var root = d3.hierarchy(treeData, function(d) { return d.children; });
	root.x0 = options.height / 2;
	root.y0 = 0;

    visit(root, n => n._children || n.children ? n.children || n._children : null);

    setLayerCount(root);
    setMaxBranchLength(root);
    sortNodes(root);
    setOrder(root);
    setDisplayOrder(root);

    var nodeXY = setXY(root);
    setMaxX(root);

    // Output the result to stdout instead of a file
    console.log(JSON.stringify(nodeXY));
});
