function graph() {
    $('.wormhole_row').each(function(index) { $(this).removeClass('highlighted'); });
    var stage = new Kinetic.Stage({
        container: 'graph',
        width: 1300,
        height: 0,
    });
    var layer = new Kinetic.Layer();
    var rowHeight = 65;
    var rectWidth = 80;
    $.getJSON('/graph', function(chains) {
        var y = 75;
        var cols = 0;
        $.each(chains, function(i, chain) {
            var stats = drawNode(chain, 90, y);
            y += stats[0] * rowHeight;
            cols = Math.max(stats[1], cols);
        });
        stage.setHeight(y);
        stage.setWidth(cols * 200);
        stage.add(layer);
    });

    function drawNode(node, x, y) {
        drawSystem(node, x, y);
        var newLines = 0;
        var newCols = 0;
        if (node.connections) {
            for (var i = 0; i < node.connections.length; i++) {
                var child = node.connections[i];
                drawLink(x, y, x + 100, y + newLines * rowHeight, child.eol, child.mass);
                var stats = drawNode(child, x + 100, y + newLines * rowHeight);
                newLines += stats[0];
                newCols = Math.max(stats[1], newCols);
            }
        }
        return [newLines || 1, newCols + 1];
    }

    var class_color = {
        'highsec': '#040',
        'lowsec': '#440',
        'nullsec': '#400',
        'unknown': '#000',
        1: '#135',
        2: '#124',
        3: '#122',
        4: '#114',
        5: '#113',
        6: '#112',
        12: '#111',
        13: '#110',
    }
    function drawSystem(system, x, y) {
        var rect = new Kinetic.Rect({
            'x': x - rectWidth / 2,
            'y': y - rectWidth / 1.75 / 2,
            'width': rectWidth,
            'height': rectWidth / 1.40,
            'fill': class_color[system['class']],
            'stroke': '#777',
            'strokeWidth': 2,
        });
        layer.add(rect);
        // draw text
        var sysNameText = new Kinetic.Text({
            'text': system.name,
            'x': x,
            'y': y-16,
            'fontSize': 12,
            'fontFamily': 'sans-serif',
            'fill': '#ccc',
        });
        var textWidth = sysNameText.getTextWidth();
        sysNameText.setX(x - textWidth / 2);
        layer.add(sysNameText);

        var sys_class;
        if (system.class && !system.class.length)
            sys_class = 'C' + system.class;
        else
            sys_class = system.class || '';
        var sysClassText = new Kinetic.Text({
            'text': sys_class,
            'x': x,
            'y': y,
            'fontSize': 11,
            'fontFamily': 'sans-serif',
            'fill': '#ccc',
        })
        textWidth = sysClassText.getTextWidth();
        sysClassText.setX(x - textWidth / 2);
        layer.add(sysClassText);

        var sysCountText = new Kinetic.Text({
            'text': system.count + ' in system',
            'x': x - 5,
            'y': y+16,
            'fontSize': 10,
            'fontFamily': 'sans-serif',
            'fill': '#ccc',
        });
        textWidth = sysCountText.getTextWidth();
        sysCountText.setX(x - textWidth / 2);
        layer.add(sysCountText);

        function _doClick(e) {
            moreInfo(system);
        }
        sysNameText.on('click', _doClick);
        sysClassText.on('click', _doClick);
        sysCountText.on('click', _doClick);
        rect.on('click', _doClick);
    }
    function drawLink(x1, y1, x2, y2, eol, mass) {
        var color;
        if (mass == 'good')
            color = '#444';
        else if (mass == 'half')
            color = '#c52';
        else if (mass == 'critical')
            color = '#b12';
        else
            color = '#777';
        var line = new Kinetic.Line({
            'x': 0,
            'y': 0,
            'points': [x1+rectWidth/2, y1, x2-rectWidth/2, y2],
            'stroke': color,
            'strokeWidth': !window.WebSocket && eol ? 1 : 2,
            'dashArray': [6, 3],
            'dashArrayEnabled': Boolean(eol),
        });
        layer.add(line);
    }
    function moreInfo(system) {
        $('#graph_info').html('<a href="/system/' + system.proper_name + '" target="_blank">System: ' + system.name + ' (' + system.class + ')</a>');
        $('.wormhole_row').each(function(item) { $(this).removeClass('highlighted'); });
        $('#wormhole_row_' + system.id).addClass('highlighted');
        $('#graph_wormhole_start').val(system.proper_name);
    }
}
