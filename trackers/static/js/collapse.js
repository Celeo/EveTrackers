$(document).ready(function() {
    $($("div.cellbottom").first()).slideDown();
    $(".celltop").click(function() {
        var bottom = $("#" + $(this).attr("for"));
        if (bottom.is(":visible"))
            bottom.slideUp(250);
        else
        {
            resetAll();
            bottom.slideDown(250);
        }
    });
});
function resetAll() {
    $(".cellbottom").each(function() {
        $(this).slideUp(250);
    });
}
