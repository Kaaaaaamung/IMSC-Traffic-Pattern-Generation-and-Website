<?php 
	$host = "gd.usc.edu";
    $sid = "ADMS";
    $username = "shuai";
    $password = "shuai2015pass";

    $config_table = "inrix_section_config";
    $geocode_table = "reverse_geocode";

    $db  =  oci_connect($username,$password,"$host/$sid");
    if(!$db){
      echo "Error : Unable to open database\n";
    } 

	if(!empty($_POST['segment_id'])):
		$segment_id = $_POST['segment_id'];
		$road = $_POST['address'];

		if ($segment_id == "truncate"){
			$sql = "truncate table $geocode_table";
		}
		else {
			$sql = "insert into $geocode_table (segment_id, road) values ($segment_id, '$road')";
		}
		$stid = oci_parse($db, $sql);
		$ret = oci_execute($stid);

		$rn = $_POST['rn'] + 1;
		$sql = "select * from (select segment_id, start_lon, end_lon, start_lat, end_lat, rownum as rn from $config_table) where rn = $rn";
		$stid = oci_parse($db, $sql);
		$ret = oci_execute($stid);
		$row = oci_fetch_row($stid);
        $lon = ($row[1] + $row[2]) / 2.0;
        $lat = ($row[3] + $row[4]) / 2.0;
        echo json_encode(array($row[0], $lon, $lat, $row[5]));
	    


	else:
		$results = array();

		$sql = "select * from (select segment_id, start_lon, end_lon, start_lat, end_lat, rownum as rn from $config_table) where rn = 1";
		$stid = oci_parse($db, $sql);
		$ret = oci_execute($stid);
		$row = oci_fetch_row($stid);
        $lon = ($row[1] + $row[2]) / 2.0;
        $lat = ($row[3] + $row[4]) / 2.0;
        $results[$row[0]] = array($lon, $lat, $row[5]);
?>
<html>
<body>
	<p />
</body>
</html>

<script src="https://code.jquery.com/jquery.min.js"></script>
<script type="text/javascript">
	$(function(){
		var locations = <?php echo json_encode($results); ?>;
		var geocoder = new google.maps.Geocoder;
		writeDB(geocoder, "truncate", "", 0);
	});

	function writeDB(geocoder, segment_id, address, rownum){
		$.post("<?php echo $_SERVER['PHP_SELF']; ?>", {segment_id: segment_id, address: address, rn: rownum}, function(data) {
			var latlng = {lat: data[2], lng: data[1]};
			var rn = data[3];
			$("p").after("segment_id: "+segment_id+"        road: "+address+"          rn: "+rownum+"        location: "+data[2]+", "+data[1]+"<br />");
			setTimeout(function(){geocode(geocoder, latlng, data[0], rn);}, 2000);
		}, "json");
	}

	function geocode(geocoder, latlng, segment_id, rn){
		geocoder.geocode({'location': latlng}, function(results, status) {
			if (status === google.maps.GeocoderStatus.OK) {
      			if (results[0]) {
      				var address = results[0].formatted_address.split(",")[0];
      				console.log(results[0].formatted_address);
      				address = address.replace(/^\d+(-\d+)?\s/g, '');
      				writeDB(geocoder, segment_id, address, rn);
				}else {
        			window.alert('No results found');
      			}
    		} else {
      			window.alert('Geocoder failed due to: ' + status);
    		}
		});
	}
</script>
<script src="https://maps.googleapis.com/maps/api/js?key=AIzaSyB86aHuCKkWMlKvTK5hmFNqAez9utzRGlA"></script>


<?php endif; ?>