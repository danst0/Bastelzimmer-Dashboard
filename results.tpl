<html>
<head>
    <title>Bastelzimmer Dashboard</title>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <link rel="stylesheet" href="static/dashboard.css" type="text/css" />
    <script src="static/jquery-2.2.1.min.js"></script>

    <script>
        var auto_refresh = setInterval(function () {
        $("#state").load(location.href + " #state");
        $("#light").load(location.href + " #light");
        $("#wx").load(location.href + " #wx");
        $("#wy").load(location.href + " #wy");
        $("#wz").load(location.href + " #wz");
        $("#eta").load(location.href + " #eta");

        $("#percentage").load(location.href + " #percentage");
        //$('#light').fadeOut('slow', function() {
        //    $(this).load(location.href + " #light);
        //});
        }, 10000); // refresh every 15000 milliseconds
        // $("#mydiv").load(location.href + " #mydiv");
    </script>
</head>
<div>
    <div class="column_1 item">
        <h1>State</h1>
        <div id="light">
            %if color == 'Red':
                <img src="static/red.png" alt="Red state" height="20%">
            %elif color == 'LightYellow':
                <img src="static/yellow.png" alt="Yellow state" height="20%">
            %elif color == 'Orange':
                <img src="static/orange.png" alt="Orange state" height="20%">
            %elif color == 'LightGreen':
                <img src="static/green.png" alt="Green state" height="20%">
            %end
        </div>
        <div id="state">
            {{state}}
        </div>
        <div id="locked">
            %if locked:
                <img src="static/lock_locked.png" alt="Locked lock" height="20%">
            %else:
                <img src="static/lock_unlocked.png" alt="Lock unlocked" height="20%">
            %end
        </div>
        <div id="sensors">
            {{sensors}}
        </div>
    </div>
    <div class="column_2 item" id="coordinates">
        <h1>Coordinates</h1>
        <div id="wx">
            X: {{wx}}
        </div>
        <div id="wy">
            Y: {{wy}}
        </div>
        <div id="wz">
            Z: {{wz}}
        </div>

    </div>

    <div class="column_3 item" id="activity">
        <h1>Completion</h1>
%if state != 'Idle' and msg != '':
        <div>
            <div id="eta">
                Time: {{ETA}} to completion (of {{total_minutes}})
            </div>
        </div>
        <div>
            <div id="percentage">
                GCode: {{percentage}}% of {{total_lines}} lines
            </div>
        </div>
%end
    </div>

</div>
<hr>
<a href="http://cnc4:8080/">Pendant</a>
</html>