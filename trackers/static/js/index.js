$(document).ready(function() {
    $('.message').bind('click', function() {
       $(this).hide(250);
    });
    $('body').keydown(function(event) {
        if (event.target.tagName !== "BODY")
            return;
        switch (event.keyCode)
        {
            case 82:
                refreshData();
                break;
        }
    });
    $('#tables').load("/tables");
    $('#sitetable').tablesorter();
    $('#wormholetable').tablesorter();
    var counter = setInterval(timer, 1000);
    function pad(n) {
        var output = n + '';
        while (output.length < 2)
            output = '0' + output;
        return output;
    }
    function timer() {
        var elements = $('td.countup');
        elements.each(function() {
            var current = $(this).text();
            if (current.indexOf(':') === -1)
                return;
            var next = current.split(':');
            if (next[1] == 59) {
                next[0] ++;
                next[1] = 0;
                next[2] = 0;
            } else if (next[2] == 59) {
                next[1] ++;
                next[2] = 0;
            } else {
                next[2] ++;
            }
            $(this).text(pad(next[0]) + ':' + pad(next[1]) + ':' + pad(next[2]));
        });
    }
    graph();
});

function refreshData() {
    $('#notify_refresh').hide();
    $('#tables').load("/tables");
    $('#graph_wormhole_start').val('');
    $('#graph_info').html('');
    graph();
    $('.modal-trigger').leanModal();
}

function addNewWormhole() {
    $.ajax({
        type: 'POST',
        url: "/",
        data: {
            data_type: 'wormhole',
            scanid: $('#w_new_scanid').val(),
            start: $('#w_new_start').val(),
            end: $('#w_new_end').val(),
            status: $('#w_new_status').val(),
            o_scanid: $('#w_new_o_scanid').val()
        },
        success: function(data) {
            refreshData();
        }
    });
}

function addNewSite() {
    $.ajax({
        type: 'POST',
        url: "/",
        data: {
            data_type: 'site',
            scanid: $('#s_new_scanid').val(),
            name: $('#s_new_name').val(),
            type: $('#s_new_type').val(),
        },
        success: function(data) {
            $('#tables').load("/tables");
        }
    });
}

function addNewWormholeGraph() {
    $.ajax({
        type: 'POST',
        url: "/",
        data: {
            graph_new_wormhole: 1,
            scanid: $('#graph_wormhole_scanid').val(),
            start: $('#graph_wormhole_start').val(),
            end: $('#graph_wormhole_end').val()
        },
        success: function(data) {
            $('#graph_wormhole_scanid').val('');
            $('#graph_wormhole_start').val('');
            $('#graph_wormhole_end').val('');
            $('#tables').load("/tables");
            graph();
        }
    });
}

function toggleSection(which) {
   $("#" + which).fadeToggle(100);
}

function edit(type, n) {
    if (type === 'wormhole') {
        var scanid = $('#wid' + n).text();
        var start = $('#wstart' + n).text();
        var end = $('#wend' + n).text();
        var status = $('#wstatus' + n).text();
        var o_scanid = $('#wo_scanid' + n).text();
        $('#wid' + n).html('<input type="text" class="uppercase short_input" id="wid' + n + '_edit" value="' + scanid + '">');
        $('#wstart' + n).html('<input type="text" class="short_input" id="wstart' + n + '_edit" value="' + start + '">');
        $('#wend' + n).html('<input type="text" class="short_input" id="wend' + n + '_edit" value="' + end + '">');
        $('#wstatus' + n).html('<input type="text" class="short_input" id="wstatus' + n + '_edit" value="' + status + '">');
        $('#wo_scanid' + n).html('<input type="text" class="uppercase short_input" id="wo_scanid' + n + '_edit" value="' + o_scanid + '">');
        $('#wlink' + n).html('<a class="label label-danger" onclick="cancel(\'wormhole\', ' + n + ')"><i class="small mdi-action-delete"></i></a> <td><a class="label label-success" onclick="save(\'wormhole\', ' + n + ')"><i class="small mdi-content-save"></i></a></td>');
    }
    else if (type === 'site') {
        var scanid = $('#sid' + n).text();
        var name = $('#sname' + n).text();
        var type = $('#stype' + n).text();
        $('#sid' + n).html('<input type="text" class="uppercase short_input" id="sid' + n + '_edit" value="' + scanid + '">');
        $('#sname' + n).html('<input type="text" class="short_input" id="sname' + n + '_edit" value="' + name + '">');
        $('#stype' + n).html('<input type="text" class="short_input" id="stype' + n + '_edit" value="' + type + '">');
        $('#slink' + n).html('<a class="label label-danger" onclick="cancel(\'site\', ' + n + ')"><i class="small mdi-action-delete"></i></a> <td><a class="label label-success" onclick="save(\'site\', ' + n + ')"><i class="small mdi-content-save"></i></a></td>');
    }
}

function cancel(type, n) {
    if (type === 'wormhole') {
        var scanid = $('#wid' + n).html().split('"')[7];
        var start = $('#wstart' + n).html().split('"')[7];
        var end = $('#wend' + n).html().split('"')[7];
        var status = $('#wstatus' + n).html().split('"')[7];
        var o_scanid = $('#wo_scanid' + n).html().split('"')[7];
        $('#wlink' + n).html('<a class="label label-warning" onclick="edit(\'wormhole\', ' + n + ')"><i class="small mdi-action-dns"></i></a>');
        $('#wid' + n).html('<a href="/wormhole/' + n + '">' + scanid + '</a>');
        $('#wstart' + n).html('<a href="/system/' + start +'">' + start + '</a>');
        $('#wend' + n).html('<a href="/system/' + end +'">' + end + '</a>');
        $('#wstatus' + n).html(status);
        $('#wo_scanid' + n).html(o_scanid);
    }
    else if (type === 'site') {
        var scanid = $('#sid' + n).html().split('"')[7];
        var name = $('#sname' + n).html().split('"')[7];
        var type = $('#stype' + n).html().split('"')[7];
        $('#slink' + n).html('<a class="label label-warning" onclick="edit(\'site\', ' + n + ')"><i class="small mdi-action-dns"></i></a>');
        $('#sid' + n).html('<a href="/site/' + n + '">' + scanid + '</a>');
        $('#sname' + n).html(name);
        $('#stype' + n).html(type);
    }
}

function save(type, n) {
    $('#js_alerts_out').text('Saving...');
    $('#js_alerts').fadeIn(250);
    if (type === 'wormhole') {
        var id = n;
        var scanid = $('#wid' + n + '_edit').val();
        var start = $('#wstart' + n + '_edit').val();
        var end = $('#wend' + n + '_edit').val();
        var status = $('#wstatus' + n + '_edit').val();
        var o_scanid = $('#wo_scanid' + n + '_edit').val();
        $.ajax({
          type: "POST",
          url: String("inlineeditwormhole/" + n),
          data: {
              id: id,
              scanid: scanid,
              start: start,
              end: end,
              status: status,
              o_scanid: o_scanid,
          },
          success: function(data) {
            $('#wlink' + n).html('<a class="label label-warning" onclick="edit(\'wormhole\',' + n + ')">Change</a>');
            $('#wid' + n).html('<a href="/wormhole/' + n + '">' + scanid.toUpperCase() + '</a>');
            $('#wstart' + n).html('<a href="/system/' + start +'">' + start + '</a>');
            $('#wend' + n).html('<a href="/system/' + end +'">' + end + '</a>');
            $('#wstatus' + n).html(status);
            $('#wo_scanid' + n).html(o_scanid.toUpperCase());
            $('#js_alerts_out').text('Saved');
            $('#js_alerts').fadeOut(3000);
          },
          fail: function(data) {
              alert('Fail: ' + data);
              cancel("wormhole", n);
              return;
          },
          error: function(data) {
              alert('Error: ' + data);
              cancel("wormhole", n);
              return;
          }
        });
    }
    else if (type === 'site') {
        var id = n;
        var scanid = $('#sid' + n + '_edit').val();
        var name = $('#sname' + n + '_edit').val();
        var type = $('#stype' + n + '_edit').val();
        $.ajax({
            type: "POST",
            url: String("inlineeditsite/" + n),
            data: {
                id: id,
                scanid: scanid,
                name: name,
                type: type,
            },
            success: function(data) {
                $('#slink' + n).html('<a class="label label-warning" onclick="edit(\'site\',' + n + ')">Change</a>');
                $('#sid' + n).html('<a href="/site/' + n + '">' + scanid.toUpperCase() + '</a>');
                $('#sname' + n).html(name);
                $('#stype' + n).html(type);
                $('#js_alerts_out').text('Saved');
                $('#js_alerts').fadeOut(3000);
            },
            fail: function(data) {
                alert('Fail: ' + data);
                cancel("site", n);
                return;
            },
            error: function(data) {
                alert('Error: ' + data);
                cancel("site", n);
                return;
            }
        });
    }
}

function checkNew(type) {
    if (type === 'wormhole') {
        if ($('#w_new_scanid').val().length == 3 && $('#w_new_start').val().length > 0 && $('#w_new_end').val().length > 0)
            $('#w_new_submit').removeAttr("disabled");
        else
            $('#w_new_submit').attr('disabled', 'disabled');
    }
    else if (type === 'site') {
        if ($('#s_new_scanid').val().length == 3 && $('#s_new_name').val().length > 0)
            $('#s_new_submit').removeAttr("disabled");
        else
            $('#s_new_submit').attr('disabled', 'disabled');   
    }
}

function updateModal(type, id) {
    $("#clickedType").text(type);
    $("#clickedID").text(id);
    $("#modal_message_final").text(type);
    $('#modalOpenModel').openModal();
}

function updateModal2(type, id) {
    $("#clickedType2").text(type);
    $("#clickedID2").text(id);
    $("#modal_message_final2").text(type);
    $('#modalCloseModel').openModal();
}
