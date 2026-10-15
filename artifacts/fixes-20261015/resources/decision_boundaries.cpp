#include "lightning_core.hpp"
#include <limits>
#include <iostream>
int main() {
{
lightning::Decision d(0.69999999999999996, 0.40000000000000002, 0);
if (d.configuration_valid()) return 1;
{ auto r = d.update(0, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 0"; return 2; } }
{ auto r = d.update(0.10000000000000001, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 1"; return 2; } }
{ auto r = d.update(0.5, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 2"; return 2; } }
{ auto r = d.update(0.90000000000000002, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 3"; return 2; } }
{ auto r = d.update(1, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 4"; return 2; } }
}
{
lightning::Decision d(std::numeric_limits<double>::quiet_NaN(), 0.40000000000000002, 2);
if (d.configuration_valid()) return 1;
{ auto r = d.update(0, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 5"; return 2; } }
{ auto r = d.update(0.10000000000000001, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 6"; return 2; } }
{ auto r = d.update(0.5, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 7"; return 2; } }
{ auto r = d.update(0.90000000000000002, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 8"; return 2; } }
{ auto r = d.update(1, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 9"; return 2; } }
}
{
lightning::Decision d(0.69999999999999996, std::numeric_limits<double>::quiet_NaN(), 2);
if (d.configuration_valid()) return 1;
{ auto r = d.update(0, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 10"; return 2; } }
{ auto r = d.update(0.10000000000000001, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 11"; return 2; } }
{ auto r = d.update(0.5, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 12"; return 2; } }
{ auto r = d.update(0.90000000000000002, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 13"; return 2; } }
{ auto r = d.update(1, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 14"; return 2; } }
}
{
lightning::Decision d(std::numeric_limits<double>::infinity(), 0.40000000000000002, 2);
if (d.configuration_valid()) return 1;
{ auto r = d.update(0, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 15"; return 2; } }
{ auto r = d.update(0.10000000000000001, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 16"; return 2; } }
{ auto r = d.update(0.5, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 17"; return 2; } }
{ auto r = d.update(0.90000000000000002, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 18"; return 2; } }
{ auto r = d.update(1, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 19"; return 2; } }
}
{
lightning::Decision d(-std::numeric_limits<double>::infinity(), 0.40000000000000002, 2);
if (d.configuration_valid()) return 1;
{ auto r = d.update(0, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 20"; return 2; } }
{ auto r = d.update(0.10000000000000001, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 21"; return 2; } }
{ auto r = d.update(0.5, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 22"; return 2; } }
{ auto r = d.update(0.90000000000000002, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 23"; return 2; } }
{ auto r = d.update(1, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 24"; return 2; } }
}
{
lightning::Decision d(0.69999999999999996, std::numeric_limits<double>::infinity(), 2);
if (d.configuration_valid()) return 1;
{ auto r = d.update(0, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 25"; return 2; } }
{ auto r = d.update(0.10000000000000001, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 26"; return 2; } }
{ auto r = d.update(0.5, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 27"; return 2; } }
{ auto r = d.update(0.90000000000000002, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 28"; return 2; } }
{ auto r = d.update(1, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 29"; return 2; } }
}
{
lightning::Decision d(0.69999999999999996, -std::numeric_limits<double>::infinity(), 2);
if (d.configuration_valid()) return 1;
{ auto r = d.update(0, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 30"; return 2; } }
{ auto r = d.update(0.10000000000000001, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 31"; return 2; } }
{ auto r = d.update(0.5, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 32"; return 2; } }
{ auto r = d.update(0.90000000000000002, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 33"; return 2; } }
{ auto r = d.update(1, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 34"; return 2; } }
}
{
lightning::Decision d(-0.10000000000000001, 0, 2);
if (d.configuration_valid()) return 1;
{ auto r = d.update(0, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 35"; return 2; } }
{ auto r = d.update(0.10000000000000001, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 36"; return 2; } }
{ auto r = d.update(0.5, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 37"; return 2; } }
{ auto r = d.update(0.90000000000000002, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 38"; return 2; } }
{ auto r = d.update(1, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 39"; return 2; } }
}
{
lightning::Decision d(0.69999999999999996, -0.10000000000000001, 2);
if (d.configuration_valid()) return 1;
{ auto r = d.update(0, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 40"; return 2; } }
{ auto r = d.update(0.10000000000000001, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 41"; return 2; } }
{ auto r = d.update(0.5, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 42"; return 2; } }
{ auto r = d.update(0.90000000000000002, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 43"; return 2; } }
{ auto r = d.update(1, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 44"; return 2; } }
}
{
lightning::Decision d(1.1000000000000001, 0.40000000000000002, 2);
if (d.configuration_valid()) return 1;
{ auto r = d.update(0, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 45"; return 2; } }
{ auto r = d.update(0.10000000000000001, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 46"; return 2; } }
{ auto r = d.update(0.5, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 47"; return 2; } }
{ auto r = d.update(0.90000000000000002, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 48"; return 2; } }
{ auto r = d.update(1, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 49"; return 2; } }
}
{
lightning::Decision d(1, 1.1000000000000001, 2);
if (d.configuration_valid()) return 1;
{ auto r = d.update(0, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 50"; return 2; } }
{ auto r = d.update(0.10000000000000001, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 51"; return 2; } }
{ auto r = d.update(0.5, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 52"; return 2; } }
{ auto r = d.update(0.90000000000000002, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 53"; return 2; } }
{ auto r = d.update(1, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 54"; return 2; } }
}
{
lightning::Decision d(0.29999999999999999, 0.69999999999999996, 1);
if (d.configuration_valid()) return 1;
{ auto r = d.update(0, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 55"; return 2; } }
{ auto r = d.update(0.10000000000000001, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 56"; return 2; } }
{ auto r = d.update(0.5, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 57"; return 2; } }
{ auto r = d.update(0.90000000000000002, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 58"; return 2; } }
{ auto r = d.update(1, true);
if (r.available || r.alarm || r.transition) { std::cerr << "invalid case 59"; return 2; } }
}
{
lightning::Decision d(0.69999999999999996, 0.40000000000000002, 2);
if (!d.configuration_valid()) return 3;
{ auto r = d.update(0.69999999999999996, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 0"; return 4; } }
{ auto r = d.update(0.69999999999999996, true);
if (r.available != true || r.alarm != true || r.transition != 1)
{ std::cerr << "Python parity step 1"; return 4; } }
{ auto r = d.update(0.40000000000000002, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 2"; return 4; } }
{ auto r = d.update(0, false);
if (r.available != false || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 3"; return 4; } }
{ auto r = d.update(0.39000000000000001, true);
if (r.available != true || r.alarm != false || r.transition != -1)
{ std::cerr << "Python parity step 4"; return 4; } }
{ auto r = d.update(0.69999999999999996, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 5"; return 4; } }
{ auto r = d.update(std::numeric_limits<double>::quiet_NaN(), true);
if (r.available != false || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 6"; return 4; } }
{ auto r = d.update(0.69999999999999996, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 7"; return 4; } }
{ auto r = d.update(std::numeric_limits<double>::infinity(), true);
if (r.available != false || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 8"; return 4; } }
{ auto r = d.update(0.69999999999999996, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 9"; return 4; } }
{ auto r = d.update(-0.10000000000000001, true);
if (r.available != false || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 10"; return 4; } }
{ auto r = d.update(0.69999999999999996, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 11"; return 4; } }
{ auto r = d.update(1.1000000000000001, true);
if (r.available != false || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 12"; return 4; } }
{ auto r = d.update(0.69999999999999996, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 13"; return 4; } }
{ auto r = d.update(0.69999999999999996, true);
if (r.available != true || r.alarm != true || r.transition != 1)
{ std::cerr << "Python parity step 14"; return 4; } }
{ auto r = d.update(0.40000000000000002, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 15"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != false || r.transition != -1)
{ std::cerr << "Python parity step 16"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 17"; return 4; } }
}
{
lightning::Decision d(0.5, 0.5, 2);
if (!d.configuration_valid()) return 3;
{ auto r = d.update(0.5, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 18"; return 4; } }
{ auto r = d.update(0.5, true);
if (r.available != true || r.alarm != true || r.transition != 1)
{ std::cerr << "Python parity step 19"; return 4; } }
{ auto r = d.update(0.5, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 20"; return 4; } }
{ auto r = d.update(0, false);
if (r.available != false || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 21"; return 4; } }
{ auto r = d.update(0.48999999999999999, true);
if (r.available != true || r.alarm != false || r.transition != -1)
{ std::cerr << "Python parity step 22"; return 4; } }
{ auto r = d.update(0.5, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 23"; return 4; } }
{ auto r = d.update(std::numeric_limits<double>::quiet_NaN(), true);
if (r.available != false || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 24"; return 4; } }
{ auto r = d.update(0.5, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 25"; return 4; } }
{ auto r = d.update(std::numeric_limits<double>::infinity(), true);
if (r.available != false || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 26"; return 4; } }
{ auto r = d.update(0.5, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 27"; return 4; } }
{ auto r = d.update(-0.10000000000000001, true);
if (r.available != false || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 28"; return 4; } }
{ auto r = d.update(0.5, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 29"; return 4; } }
{ auto r = d.update(1.1000000000000001, true);
if (r.available != false || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 30"; return 4; } }
{ auto r = d.update(0.5, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 31"; return 4; } }
{ auto r = d.update(0.5, true);
if (r.available != true || r.alarm != true || r.transition != 1)
{ std::cerr << "Python parity step 32"; return 4; } }
{ auto r = d.update(0.5, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 33"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != false || r.transition != -1)
{ std::cerr << "Python parity step 34"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 35"; return 4; } }
}
{
lightning::Decision d(0, 0, 2);
if (!d.configuration_valid()) return 3;
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 36"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != true || r.transition != 1)
{ std::cerr << "Python parity step 37"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 38"; return 4; } }
{ auto r = d.update(0, false);
if (r.available != false || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 39"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 40"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 41"; return 4; } }
{ auto r = d.update(std::numeric_limits<double>::quiet_NaN(), true);
if (r.available != false || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 42"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 43"; return 4; } }
{ auto r = d.update(std::numeric_limits<double>::infinity(), true);
if (r.available != false || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 44"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 45"; return 4; } }
{ auto r = d.update(-0.10000000000000001, true);
if (r.available != false || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 46"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 47"; return 4; } }
{ auto r = d.update(1.1000000000000001, true);
if (r.available != false || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 48"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 49"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 50"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 51"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 52"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 53"; return 4; } }
}
{
lightning::Decision d(1, 1, 1);
if (!d.configuration_valid()) return 3;
{ auto r = d.update(1, true);
if (r.available != true || r.alarm != true || r.transition != 1)
{ std::cerr << "Python parity step 54"; return 4; } }
{ auto r = d.update(1, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 55"; return 4; } }
{ auto r = d.update(1, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 56"; return 4; } }
{ auto r = d.update(0, false);
if (r.available != false || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 57"; return 4; } }
{ auto r = d.update(0.98999999999999999, true);
if (r.available != true || r.alarm != false || r.transition != -1)
{ std::cerr << "Python parity step 58"; return 4; } }
{ auto r = d.update(1, true);
if (r.available != true || r.alarm != true || r.transition != 1)
{ std::cerr << "Python parity step 59"; return 4; } }
{ auto r = d.update(std::numeric_limits<double>::quiet_NaN(), true);
if (r.available != false || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 60"; return 4; } }
{ auto r = d.update(1, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 61"; return 4; } }
{ auto r = d.update(std::numeric_limits<double>::infinity(), true);
if (r.available != false || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 62"; return 4; } }
{ auto r = d.update(1, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 63"; return 4; } }
{ auto r = d.update(-0.10000000000000001, true);
if (r.available != false || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 64"; return 4; } }
{ auto r = d.update(1, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 65"; return 4; } }
{ auto r = d.update(1.1000000000000001, true);
if (r.available != false || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 66"; return 4; } }
{ auto r = d.update(1, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 67"; return 4; } }
{ auto r = d.update(1, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 68"; return 4; } }
{ auto r = d.update(1, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 69"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != false || r.transition != -1)
{ std::cerr << "Python parity step 70"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 71"; return 4; } }
}
{
lightning::Decision d(0.17412868142127991, 0.17412868142127991, 2);
if (!d.configuration_valid()) return 3;
{ auto r = d.update(0.17412868142127991, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 72"; return 4; } }
{ auto r = d.update(0.17412868142127991, true);
if (r.available != true || r.alarm != true || r.transition != 1)
{ std::cerr << "Python parity step 73"; return 4; } }
{ auto r = d.update(0.17412868142127991, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 74"; return 4; } }
{ auto r = d.update(0, false);
if (r.available != false || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 75"; return 4; } }
{ auto r = d.update(0.1641286814212799, true);
if (r.available != true || r.alarm != false || r.transition != -1)
{ std::cerr << "Python parity step 76"; return 4; } }
{ auto r = d.update(0.17412868142127991, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 77"; return 4; } }
{ auto r = d.update(std::numeric_limits<double>::quiet_NaN(), true);
if (r.available != false || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 78"; return 4; } }
{ auto r = d.update(0.17412868142127991, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 79"; return 4; } }
{ auto r = d.update(std::numeric_limits<double>::infinity(), true);
if (r.available != false || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 80"; return 4; } }
{ auto r = d.update(0.17412868142127991, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 81"; return 4; } }
{ auto r = d.update(-0.10000000000000001, true);
if (r.available != false || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 82"; return 4; } }
{ auto r = d.update(0.17412868142127991, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 83"; return 4; } }
{ auto r = d.update(1.1000000000000001, true);
if (r.available != false || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 84"; return 4; } }
{ auto r = d.update(0.17412868142127991, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 85"; return 4; } }
{ auto r = d.update(0.17412868142127991, true);
if (r.available != true || r.alarm != true || r.transition != 1)
{ std::cerr << "Python parity step 86"; return 4; } }
{ auto r = d.update(0.17412868142127991, true);
if (r.available != true || r.alarm != true || r.transition != 0)
{ std::cerr << "Python parity step 87"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != false || r.transition != -1)
{ std::cerr << "Python parity step 88"; return 4; } }
{ auto r = d.update(0, true);
if (r.available != true || r.alarm != false || r.transition != 0)
{ std::cerr << "Python parity step 89"; return 4; } }
}
std::cout << "PASS: 12 invalid configurations, 60 rejected decisions, 90 Python parity steps";
return 0;
}
