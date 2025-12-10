<?php
require_once __DIR__ . "/env.php";

load_env(__DIR__ . "/.env");

$host   = $_ENV["DB_HOST"];
$user   = $_ENV["DB_USER"];
$pass   = $_ENV["DB_PASS"];
$dbname = $_ENV["DB_NAME"];

$conn = new mysqli($host, $user, $pass, $dbname);

if ($conn->connect_error) {
    header("Content-Type: text/plain; charset=utf-8");
    die("db_error");
}

if (isset($_REQUEST['state'])) {
    $state = ($_REQUEST['state'] === 'on') ? 'on' : 'off';

    $stmt = $conn->prepare("UPDATE pump_status SET state = ?, updated_at = NOW() WHERE id = 1");
    $stmt->bind_param("s", $state);
    $stmt->execute();
    $stmt->close();

    header("Content-Type: text/plain; charset=utf-8");
    echo $state;
    exit;
}

if (isset($_GET['get'])) {
    $result = $conn->query("SELECT state FROM pump_status WHERE id = 1 LIMIT 1");

    if ($result && $row = $result->fetch_assoc()) {
        $state = ($row['state'] === 'on') ? 'on' : 'off';
    } else {
        $state = 'off';
    }

    header("Content-Type: text/plain; charset=utf-8");
    echo $state;
    exit;
}

header("Content-Type: text/plain; charset=utf-8");
echo "Use ?state=on|off or ?get=1";
