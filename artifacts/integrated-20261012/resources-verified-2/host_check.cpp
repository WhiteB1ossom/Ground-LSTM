#include "lightning_core.hpp"
#include "preprocessing_constants.hpp"
#include <iostream>
int main(){
lightning::CausalCurrent<5> state; lightning::Ring<114,15> ring; std::array<float,15> out;
{
state.update(1767225600000000000LL, {0.125,0.25,0.375,0.5,0.625}, {1,1,1,1,1});
bool valid=state.features<15>(1767225600000000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.1442912817001343,-0.59885835647583008,470.26406860351562,-118.87675476074219,7.4425539970397949,0,0,0,0,0,0,0,-1.5666989088058472,-1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225600000000000LL,out,valid)) return 4;
}
{
state.update(1767225600100000000LL, {0.127,0.252,0.377,0.502,0.627}, {1,1,0,0,1});
bool valid=state.features<15>(1767225600100000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.1414746046066284,-0.59391283988952637,470.26406860351562,-118.87675476074219,7.4666376113891602,0,0,0,0,0,0,0,-1.2185436487197876,-1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225600100000000LL,out,valid)) return 4;
}
{
state.update(1767225600200000000LL, {0.129,0.254,0.379,0.504,0.629}, {1,1,0,0,1});
bool valid=state.features<15>(1767225600200000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.1386580467224121,-0.58896732330322266,470.26406860351562,-118.87675476074219,7.4907212257385254,0,0,0,0,0,0,0,-0.87038826942443848,-0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225600200000000LL,out,valid)) return 4;
}
{
state.update(1767225600300000000LL, {0.13100000000000001,0.25600000000000001,0.38100000000000001,0.50600000000000001,0.63100000000000001}, {1,1,0,0,1});
bool valid=state.features<15>(1767225600300000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.1358414888381958,-0.58402180671691895,470.26406860351562,-118.87675476074219,7.5148053169250488,0,0,0,0,0,0,0,-0.52223294973373413,-0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225600300000000LL,out,valid)) return 4;
}
{
state.update(1767225600400000000LL, {0.13300000000000001,0.25800000000000001,0.38300000000000001,0.50800000000000001,0.63300000000000001}, {1,1,0,0,1});
bool valid=state.features<15>(1767225600400000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.1330248117446899,-0.57907634973526001,470.26406860351562,-118.87675476074219,7.5388889312744141,0,0,0,0,0,0,0,-0.17407765984535217,-0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225600400000000LL,out,valid)) return 4;
}
{
state.update(1767225600500000000LL, {0.13500000000000001,0.26000000000000001,0.38500000000000001,0.51000000000000001,0.63500000000000001}, {1,1,0,0,1});
bool valid=state.features<15>(1767225600500000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.1302082538604736,-0.5741308331489563,470.26406860351562,-118.87675476074219,7.5629725456237793,0,0,0,0,0,0,0,0.17407765984535217,0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225600500000000LL,out,valid)) return 4;
}
{
state.update(1767225600600000000LL, {0.13700000000000001,0.26200000000000001,0.38700000000000001,0.51200000000000001,0.63700000000000001}, {1,1,0,0,1});
bool valid=state.features<15>(1767225600600000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.1273916959762573,-0.56918531656265259,470.26406860351562,-118.87675476074219,7.5870566368103027,0,0,0,0,0,0,0,0.52223294973373413,0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225600600000000LL,out,valid)) return 4;
}
{
state.update(1767225600700000000LL, {0.13900000000000001,0.26400000000000001,0.38900000000000001,0.51400000000000001,0.63900000000000001}, {1,1,0,0,1});
bool valid=state.features<15>(1767225600700000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.1245750188827515,-0.56423979997634888,470.26406860351562,-118.87675476074219,7.611140251159668,0,0,0,0,0,0,0,0.87038826942443848,0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225600700000000LL,out,valid)) return 4;
}
{
state.update(1767225600800000000LL, {0.14100000000000001,0.26600000000000001,0.39100000000000001,0.51600000000000001,0.64100000000000001}, {1,1,0,0,1});
bool valid=state.features<15>(1767225600800000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.1217584609985352,-0.55929428339004517,470.26406860351562,-118.87675476074219,7.6352238655090332,0,0,0,0,0,0,0,1.2185436487197876,1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225600800000000LL,out,valid)) return 4;
}
{
state.update(1767225600900000000LL, {0.14300000000000002,0.26800000000000002,0.39300000000000002,0.51800000000000002,0.64300000000000002}, {1,1,0,0,1});
bool valid=state.features<15>(1767225600900000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.1189419031143188,-0.55434882640838623,470.26406860351562,-118.87675476074219,7.6593079566955566,0,0,0,0,0,0,0,1.5666989088058472,1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225600900000000LL,out,valid)) return 4;
}
{
state.update(1767225601000000000LL, {0.14499999999999999,0.27000000000000002,0.39500000000000002,0.52000000000000002,0.64500000000000002}, {1,1,1,1,1});
bool valid=state.features<15>(1767225601000000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.116125226020813,-0.54940330982208252,495.45989990234375,-118.86639404296875,7.6833915710449219,0,0,0,0,0,0,0,-1.5666989088058472,-1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225601000000000LL,out,valid)) return 4;
}
{
state.update(1767225601100000000LL, {0.14699999999999999,0.27200000000000002,0.39700000000000002,0.52200000000000002,0.64700000000000002}, {1,1,0,0,1});
bool valid=state.features<15>(1767225601100000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.1133086681365967,-0.54445779323577881,495.45989990234375,-118.86639404296875,7.7074751853942871,0,0,0,0,0,0,0,-1.2185436487197876,-1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225601100000000LL,out,valid)) return 4;
}
{
state.update(1767225601200000000LL, {0.14899999999999999,0.27400000000000002,0.39900000000000002,0.52400000000000002,0.64900000000000002}, {1,1,0,0,1});
bool valid=state.features<15>(1767225601200000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.1104921102523804,-0.5395122766494751,495.45989990234375,-118.86639404296875,7.7315592765808105,0,0,0,0,0,0,0,-0.87038826942443848,-0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225601200000000LL,out,valid)) return 4;
}
{
state.update(1767225601300000000LL, {0.151,0.27600000000000002,0.40100000000000002,0.52600000000000002,0.65100000000000002}, {1,1,0,0,1});
bool valid=state.features<15>(1767225601300000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.1076754331588745,-0.53456676006317139,495.45989990234375,-118.86639404296875,7.7556428909301758,0,0,0,0,0,0,0,-0.52223294973373413,-0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225601300000000LL,out,valid)) return 4;
}
{
state.update(1767225601400000000LL, {0.153,0.27800000000000002,0.40300000000000002,0.52800000000000002,0.65300000000000002}, {1,1,0,0,1});
bool valid=state.features<15>(1767225601400000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.1048588752746582,-0.52962124347686768,495.45989990234375,-118.86639404296875,7.779726505279541,0,0,0,0,0,0,0,-0.17407765984535217,-0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225601400000000LL,out,valid)) return 4;
}
{
state.update(1767225601500000000LL, {0.155,0.28000000000000003,0.40500000000000003,0.53000000000000003,0.65500000000000003}, {1,1,0,0,1});
bool valid=state.features<15>(1767225601500000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.1020423173904419,-0.52467578649520874,495.45989990234375,-118.86639404296875,7.8038105964660645,0,0,0,0,0,0,0,0.17407765984535217,0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225601500000000LL,out,valid)) return 4;
}
{
state.update(1767225601600000000LL, {0.157,0.28200000000000003,0.40700000000000003,0.53200000000000003,0.65700000000000003}, {1,1,0,0,1});
bool valid=state.features<15>(1767225601600000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.099225640296936,-0.51973026990890503,495.45989990234375,-118.86639404296875,7.8278942108154297,0,0,0,0,0,0,0,0.52223294973373413,0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225601600000000LL,out,valid)) return 4;
}
{
state.update(1767225601700000000LL, {0.159,0.28400000000000003,0.40900000000000003,0.53400000000000003,0.65900000000000003}, {1,1,0,0,1});
bool valid=state.features<15>(1767225601700000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0964090824127197,-0.51478475332260132,495.45989990234375,-118.86639404296875,7.8519778251647949,0,0,0,0,0,0,0,0.87038826942443848,0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225601700000000LL,out,valid)) return 4;
}
{
state.update(1767225601800000000LL, {0.161,0.28600000000000003,0.41100000000000003,0.53600000000000003,0.66100000000000003}, {1,1,0,0,1});
bool valid=state.features<15>(1767225601800000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0935925245285034,-0.50983923673629761,495.45989990234375,-118.86639404296875,7.8760619163513184,0,0,0,0,0,0,0,1.2185436487197876,1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225601800000000LL,out,valid)) return 4;
}
{
state.update(1767225601900000000LL, {0.16300000000000001,0.28799999999999998,0.41299999999999998,0.53800000000000003,0.66300000000000003}, {1,1,0,0,1});
bool valid=state.features<15>(1767225601900000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0907758474349976,-0.5048937201499939,495.45989990234375,-118.86639404296875,7.9001455307006836,0,0,0,0,0,0,0,1.5666989088058472,1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225601900000000LL,out,valid)) return 4;
}
{
state.update(1767225602000000000LL, {0.16500000000000001,0.28999999999999998,0.41499999999999998,0.54000000000000004,0.66500000000000004}, {1,1,1,1,1});
bool valid=state.features<15>(1767225602000000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0879592895507812,-0.49994823336601257,520.65570068359375,-118.85603332519531,7.9242291450500488,0,0,0,0,0,0,0,-1.5666989088058472,-1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225602000000000LL,out,valid)) return 4;
}
{
state.update(1767225602100000000LL, {0.16700000000000001,0.29199999999999998,0.41699999999999998,0.54200000000000004,0.66700000000000004}, {1,1,0,0,1});
bool valid=state.features<15>(1767225602100000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0851427316665649,-0.49500274658203125,520.65570068359375,-118.85603332519531,7.9483132362365723,0,0,0,0,0,0,0,-1.2185436487197876,-1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225602100000000LL,out,valid)) return 4;
}
{
state.update(1767225602200000000LL, {0.16899999999999998,0.29399999999999998,0.41899999999999998,0.54400000000000004,0.66900000000000004}, {1,1,0,0,1});
bool valid=state.features<15>(1767225602200000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0823260545730591,-0.49005722999572754,520.65570068359375,-118.85603332519531,7.9723968505859375,0,0,0,0,0,0,0,-0.87038826942443848,-0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225602200000000LL,out,valid)) return 4;
}
{
state.update(1767225602300000000LL, {0.17099999999999999,0.29599999999999999,0.42099999999999999,0.54600000000000004,0.67100000000000004}, {1,1,0,0,1});
bool valid=state.features<15>(1767225602300000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0795094966888428,-0.48511171340942383,520.65570068359375,-118.85603332519531,7.9964804649353027,0,0,0,0,0,0,0,-0.52223294973373413,-0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225602300000000LL,out,valid)) return 4;
}
{
state.update(1767225602400000000LL, {0.17299999999999999,0.29799999999999999,0.42299999999999999,0.54800000000000004,0.67300000000000004}, {1,1,0,0,1});
bool valid=state.features<15>(1767225602400000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0766929388046265,-0.4801662266254425,520.65570068359375,-118.85603332519531,8.020564079284668,0,0,0,0,0,0,0,-0.17407765984535217,-0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225602400000000LL,out,valid)) return 4;
}
{
state.update(1767225602500000000LL, {0.17499999999999999,0.29999999999999999,0.42499999999999999,0.55000000000000004,0.67500000000000004}, {1,1,0,0,1});
bool valid=state.features<15>(1767225602500000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0738762617111206,-0.47522071003913879,520.65570068359375,-118.85603332519531,8.0446481704711914,0,0,0,0,0,0,0,0.17407765984535217,0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225602500000000LL,out,valid)) return 4;
}
{
state.update(1767225602600000000LL, {0.17699999999999999,0.30199999999999999,0.42699999999999999,0.55200000000000005,0.67700000000000005}, {1,1,0,0,1});
bool valid=state.features<15>(1767225602600000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0710597038269043,-0.47027522325515747,520.65570068359375,-118.85603332519531,8.0687322616577148,0,0,0,0,0,0,0,0.52223294973373413,0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225602600000000LL,out,valid)) return 4;
}
{
state.update(1767225602700000000LL, {0.17899999999999999,0.30399999999999999,0.42899999999999999,0.55400000000000005,0.67900000000000005}, {1,1,0,0,1});
bool valid=state.features<15>(1767225602700000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.068243145942688,-0.46532970666885376,520.65570068359375,-118.85603332519531,8.0928153991699219,0,0,0,0,0,0,0,0.87038826942443848,0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225602700000000LL,out,valid)) return 4;
}
{
state.update(1767225602800000000LL, {0.18099999999999999,0.30599999999999999,0.43099999999999999,0.55600000000000005,0.68100000000000005}, {1,1,0,0,1});
bool valid=state.features<15>(1767225602800000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0654264688491821,-0.46038419008255005,520.65570068359375,-118.85603332519531,8.1168994903564453,0,0,0,0,0,0,0,1.2185436487197876,1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225602800000000LL,out,valid)) return 4;
}
{
state.update(1767225602900000000LL, {0.183,0.308,0.433,0.55800000000000005,0.68300000000000005}, {1,1,0,0,1});
bool valid=state.features<15>(1767225602900000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0626099109649658,-0.45543870329856873,520.65570068359375,-118.85603332519531,8.1409835815429688,0,0,0,0,0,0,0,1.5666989088058472,1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225602900000000LL,out,valid)) return 4;
}
{
state.update(1767225603000000000LL, {0.185,0.31,0.435,0.56000000000000005,0.68500000000000005}, {1,1,1,1,1});
bool valid=state.features<15>(1767225603000000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0597933530807495,-0.45049318671226501,545.8515625,-118.84567260742188,8.1650667190551758,0,0,0,0,0,0,0,-1.5666989088058472,-1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225603000000000LL,out,valid)) return 4;
}
{
state.update(1767225603100000000LL, {0.187,0.312,0.437,0.56200000000000006,0.68700000000000006}, {1,1,0,0,1});
bool valid=state.features<15>(1767225603100000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0569766759872437,-0.44554769992828369,545.8515625,-118.84567260742188,8.1891508102416992,0,0,0,0,0,0,0,-1.2185436487197876,-1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225603100000000LL,out,valid)) return 4;
}
{
state.update(1767225603200000000LL, {0.189,0.314,0.439,0.56400000000000006,0.68900000000000006}, {1,1,0,0,1});
bool valid=state.features<15>(1767225603200000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0541601181030273,-0.44060218334197998,545.8515625,-118.84567260742188,8.2132349014282227,0,0,0,0,0,0,0,-0.87038826942443848,-0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225603200000000LL,out,valid)) return 4;
}
{
state.update(1767225603300000000LL, {0.191,0.316,0.441,0.56600000000000006,0.69100000000000006}, {1,1,0,0,1});
bool valid=state.features<15>(1767225603300000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.051343560218811,-0.43565666675567627,545.8515625,-118.84567260742188,8.2373180389404297,0,0,0,0,0,0,0,-0.52223294973373413,-0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225603300000000LL,out,valid)) return 4;
}
{
state.update(1767225603400000000LL, {0.193,0.318,0.443,0.56800000000000006,0.69300000000000006}, {1,1,0,0,1});
bool valid=state.features<15>(1767225603400000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0485268831253052,-0.43071117997169495,545.8515625,-118.84567260742188,8.2614021301269531,0,0,0,0,0,0,0,-0.17407765984535217,-0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225603400000000LL,out,valid)) return 4;
}
{
state.update(1767225603500000000LL, {0.19500000000000001,0.32000000000000001,0.44500000000000001,0.57000000000000006,0.69500000000000006}, {1,1,0,0,1});
bool valid=state.features<15>(1767225603500000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0457103252410889,-0.42576566338539124,545.8515625,-118.84567260742188,8.2854862213134766,0,0,0,0,0,0,0,0.17407765984535217,0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225603500000000LL,out,valid)) return 4;
}
{
state.update(1767225603600000000LL, {0.19700000000000001,0.32200000000000001,0.44700000000000001,0.57200000000000006,0.69700000000000006}, {1,1,0,0,1});
bool valid=state.features<15>(1767225603600000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0428937673568726,-0.42082017660140991,545.8515625,-118.84567260742188,8.3095693588256836,0,0,0,0,0,0,0,0.52223294973373413,0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225603600000000LL,out,valid)) return 4;
}
{
state.update(1767225603700000000LL, {0.19900000000000001,0.32400000000000001,0.44900000000000001,0.57399999999999995,0.69899999999999995}, {1,1,0,0,1});
bool valid=state.features<15>(1767225603700000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0400770902633667,-0.4158746600151062,545.8515625,-118.84567260742188,8.333653450012207,0,0,0,0,0,0,0,0.87038826942443848,0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225603700000000LL,out,valid)) return 4;
}
{
state.update(1767225603800000000LL, {0.20100000000000001,0.32600000000000001,0.45100000000000001,0.57599999999999996,0.70099999999999996}, {1,1,0,0,1});
bool valid=state.features<15>(1767225603800000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0372605323791504,-0.41092914342880249,545.8515625,-118.84567260742188,8.3577375411987305,0,0,0,0,0,0,0,1.2185436487197876,1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225603800000000LL,out,valid)) return 4;
}
{
state.update(1767225603900000000LL, {0.20300000000000001,0.32800000000000001,0.45300000000000001,0.57799999999999996,0.70299999999999996}, {1,1,0,0,1});
bool valid=state.features<15>(1767225603900000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0344439744949341,-0.40598365664482117,545.8515625,-118.84567260742188,8.3818206787109375,0,0,0,0,0,0,0,1.5666989088058472,1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225603900000000LL,out,valid)) return 4;
}
{
state.update(1767225604000000000LL, {0.20500000000000002,0.33000000000000002,0.45500000000000002,0.57999999999999996,0.70499999999999996}, {1,1,1,1,1});
bool valid=state.features<15>(1767225604000000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0316272974014282,-0.40103814005851746,571.04736328125,-118.83531188964844,8.4059047698974609,0,0,0,0,0,0,0,-1.5666989088058472,-1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225604000000000LL,out,valid)) return 4;
}
{
state.update(1767225604100000000LL, {0.20700000000000002,0.33200000000000002,0.45700000000000002,0.58199999999999996,0.70699999999999996}, {1,1,0,0,1});
bool valid=state.features<15>(1767225604100000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0288107395172119,-0.39609262347221375,571.04736328125,-118.83531188964844,8.4299888610839844,0,0,0,0,0,0,0,-1.2185436487197876,-1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225604100000000LL,out,valid)) return 4;
}
{
state.update(1767225604200000000LL, {0.20900000000000002,0.33400000000000002,0.45900000000000002,0.58399999999999996,0.70899999999999996}, {1,1,0,0,1});
bool valid=state.features<15>(1767225604200000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0259941816329956,-0.39114713668823242,571.04736328125,-118.83531188964844,8.4540719985961914,0,0,0,0,0,0,0,-0.87038826942443848,-0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225604200000000LL,out,valid)) return 4;
}
{
state.update(1767225604300000000LL, {0.21100000000000002,0.33600000000000002,0.46100000000000002,0.58599999999999997,0.71099999999999997}, {1,1,0,0,1});
bool valid=state.features<15>(1767225604300000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0231775045394897,-0.38620162010192871,571.04736328125,-118.83531188964844,8.4781560897827148,0,0,0,0,0,0,0,-0.52223294973373413,-0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225604300000000LL,out,valid)) return 4;
}
{
state.update(1767225604400000000LL, {0.21299999999999999,0.33799999999999997,0.46299999999999997,0.58799999999999997,0.71299999999999997}, {1,1,0,0,1});
bool valid=state.features<15>(1767225604400000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0203609466552734,-0.38125613331794739,571.04736328125,-118.83531188964844,8.5022401809692383,0,0,0,0,0,0,0,-0.17407765984535217,-0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225604400000000LL,out,valid)) return 4;
}
{
state.update(1767225604500000000LL, {0.215,0.33999999999999997,0.46499999999999997,0.58999999999999997,0.71499999999999997}, {1,1,0,0,1});
bool valid=state.features<15>(1767225604500000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0175443887710571,-0.37631061673164368,571.04736328125,-118.83531188964844,8.5263233184814453,0,0,0,0,0,0,0,0.17407765984535217,0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225604500000000LL,out,valid)) return 4;
}
{
state.update(1767225604600000000LL, {0.217,0.34199999999999997,0.46699999999999997,0.59199999999999997,0.71699999999999997}, {1,1,0,0,1});
bool valid=state.features<15>(1767225604600000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0147277116775513,-0.37136510014533997,571.04736328125,-118.83531188964844,8.5504074096679688,0,0,0,0,0,0,0,0.52223294973373413,0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225604600000000LL,out,valid)) return 4;
}
{
state.update(1767225604700000000LL, {0.219,0.34399999999999997,0.46899999999999997,0.59399999999999997,0.71899999999999997}, {1,1,0,0,1});
bool valid=state.features<15>(1767225604700000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.011911153793335,-0.36641961336135864,571.04736328125,-118.83531188964844,8.5744915008544922,0,0,0,0,0,0,0,0.87038826942443848,0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225604700000000LL,out,valid)) return 4;
}
{
state.update(1767225604800000000LL, {0.221,0.34599999999999997,0.47099999999999997,0.59599999999999997,0.72099999999999997}, {1,1,0,0,1});
bool valid=state.features<15>(1767225604800000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0090945959091187,-0.36147409677505493,571.04736328125,-118.83531188964844,8.5985746383666992,0,0,0,0,0,0,0,1.2185436487197876,1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225604800000000LL,out,valid)) return 4;
}
{
state.update(1767225604900000000LL, {0.223,0.34799999999999998,0.47299999999999998,0.59799999999999998,0.72299999999999998}, {1,1,0,0,1});
bool valid=state.features<15>(1767225604900000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0062779188156128,-0.35652860999107361,571.04736328125,-118.83531188964844,8.6226587295532227,0,0,0,0,0,0,0,1.5666989088058472,1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225604900000000LL,out,valid)) return 4;
}
{
state.update(1767225605000000000LL, {0.22500000000000001,0.34999999999999998,0.47499999999999998,0.59999999999999998,0.72499999999999998}, {1,1,1,1,1});
bool valid=state.features<15>(1767225605000000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0034613609313965,-0.3515830934047699,596.24322509765625,-118.824951171875,8.6467428207397461,0,0,0,0,0,0,0,-1.5666989088058472,-1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225605000000000LL,out,valid)) return 4;
}
{
state.update(1767225605100000000LL, {0.22700000000000001,0.35199999999999998,0.47699999999999998,0.60199999999999998,0.72699999999999998}, {1,1,0,0,1});
bool valid=state.features<15>(1767225605100000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-1.0006448030471802,-0.34663757681846619,596.24322509765625,-118.824951171875,8.6708259582519531,0,0,0,0,0,0,0,-1.2185436487197876,-1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225605100000000LL,out,valid)) return 4;
}
{
state.update(1767225605200000000LL, {0.22900000000000001,0.35399999999999998,0.47899999999999998,0.60399999999999998,0.72899999999999998}, {1,1,0,0,1});
bool valid=state.features<15>(1767225605200000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.99782812595367432,-0.34169209003448486,596.24322509765625,-118.824951171875,8.6949100494384766,0,0,0,0,0,0,0,-0.87038826942443848,-0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225605200000000LL,out,valid)) return 4;
}
{
state.update(1767225605300000000LL, {0.23099999999999998,0.35599999999999998,0.48099999999999998,0.60599999999999998,0.73099999999999998}, {1,1,0,0,1});
bool valid=state.features<15>(1767225605300000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.99501156806945801,-0.33674657344818115,596.24322509765625,-118.824951171875,8.718994140625,0,0,0,0,0,0,0,-0.52223294973373413,-0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225605300000000LL,out,valid)) return 4;
}
{
state.update(1767225605400000000LL, {0.23299999999999998,0.35799999999999998,0.48299999999999998,0.60799999999999998,0.73299999999999998}, {1,1,0,0,1});
bool valid=state.features<15>(1767225605400000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.99219495058059692,-0.33180108666419983,596.24322509765625,-118.824951171875,8.743077278137207,0,0,0,0,0,0,0,-0.17407765984535217,-0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225605400000000LL,out,valid)) return 4;
}
{
state.update(1767225605500000000LL, {0.23499999999999999,0.35999999999999999,0.48499999999999999,0.60999999999999999,0.73499999999999999}, {1,1,0,0,1});
bool valid=state.features<15>(1767225605500000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.98937833309173584,-0.32685557007789612,596.24322509765625,-118.824951171875,8.7671613693237305,0,0,0,0,0,0,0,0.17407765984535217,0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225605500000000LL,out,valid)) return 4;
}
{
state.update(1767225605600000000LL, {0.23699999999999999,0.36199999999999999,0.48699999999999999,0.61199999999999999,0.73699999999999999}, {1,1,0,0,1});
bool valid=state.features<15>(1767225605600000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.98656177520751953,-0.32191005349159241,596.24322509765625,-118.824951171875,8.7912454605102539,0,0,0,0,0,0,0,0.52223294973373413,0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225605600000000LL,out,valid)) return 4;
}
{
state.update(1767225605700000000LL, {0.23899999999999999,0.36399999999999999,0.48899999999999999,0.61399999999999999,0.73899999999999999}, {1,1,0,0,1});
bool valid=state.features<15>(1767225605700000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.98374515771865845,-0.31696456670761108,596.24322509765625,-118.824951171875,8.8153285980224609,0,0,0,0,0,0,0,0.87038826942443848,0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225605700000000LL,out,valid)) return 4;
}
{
state.update(1767225605800000000LL, {0.24099999999999999,0.36599999999999999,0.49099999999999999,0.61599999999999999,0.74099999999999999}, {1,1,0,0,1});
bool valid=state.features<15>(1767225605800000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.98092854022979736,-0.31201905012130737,596.24322509765625,-118.824951171875,8.8394126892089844,0,0,0,0,0,0,0,1.2185436487197876,1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225605800000000LL,out,valid)) return 4;
}
{
state.update(1767225605900000000LL, {0.24299999999999999,0.36799999999999999,0.49299999999999999,0.61799999999999999,0.74299999999999999}, {1,1,0,0,1});
bool valid=state.features<15>(1767225605900000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.97811198234558105,-0.30707353353500366,596.24322509765625,-118.824951171875,8.8634967803955078,0,0,0,0,0,0,0,1.5666989088058472,1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225605900000000LL,out,valid)) return 4;
}
{
state.update(1767225606000000000LL, {0.245,0.37,0.495,0.62,0.745}, {1,1,1,1,1});
bool valid=state.features<15>(1767225606000000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.97529536485671997,-0.30212804675102234,621.43902587890625,-118.81459045410156,8.8875799179077148,0,0,0,0,0,0,0,-1.5666989088058472,-1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225606000000000LL,out,valid)) return 4;
}
{
state.update(1767225606100000000LL, {0.247,0.372,0.497,0.622,0.747}, {1,1,0,0,1});
bool valid=state.features<15>(1767225606100000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.97247874736785889,-0.29718253016471863,621.43902587890625,-118.81459045410156,8.9116640090942383,0,0,0,0,0,0,0,-1.2185436487197876,-1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225606100000000LL,out,valid)) return 4;
}
{
state.update(1767225606200000000LL, {0.249,0.374,0.499,0.624,0.749}, {1,1,0,0,1});
bool valid=state.features<15>(1767225606200000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.96966218948364258,-0.2922370433807373,621.43902587890625,-118.81459045410156,8.9357471466064453,0,0,0,0,0,0,0,-0.87038826942443848,-0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225606200000000LL,out,valid)) return 4;
}
{
state.update(1767225606300000000LL, {0.251,0.376,0.501,0.626,0.751}, {1,1,0,0,1});
bool valid=state.features<15>(1767225606300000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.96684557199478149,-0.28729152679443359,621.43902587890625,-118.81459045410156,8.9598312377929688,0,0,0,0,0,0,0,-0.52223294973373413,-0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225606300000000LL,out,valid)) return 4;
}
{
state.update(1767225606400000000LL, {0.253,0.378,0.503,0.628,0.753}, {1,1,0,0,1});
bool valid=state.features<15>(1767225606400000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.96402895450592041,-0.28234601020812988,621.43902587890625,-118.81459045410156,8.9839153289794922,0,0,0,0,0,0,0,-0.17407765984535217,-0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225606400000000LL,out,valid)) return 4;
}
{
state.update(1767225606500000000LL, {0.255,0.38,0.505,0.63,0.755}, {1,1,0,0,1});
bool valid=state.features<15>(1767225606500000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.9612123966217041,-0.27740052342414856,621.43902587890625,-118.81459045410156,9.0079984664916992,0,0,0,0,0,0,0,0.17407765984535217,0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225606500000000LL,out,valid)) return 4;
}
{
state.update(1767225606600000000LL, {0.25700000000000001,0.38200000000000001,0.50700000000000001,0.63200000000000001,0.75700000000000001}, {1,1,0,0,1});
bool valid=state.features<15>(1767225606600000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.95839577913284302,-0.27245500683784485,621.43902587890625,-118.81459045410156,9.0320825576782227,0,0,0,0,0,0,0,0.52223294973373413,0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225606600000000LL,out,valid)) return 4;
}
{
state.update(1767225606700000000LL, {0.25900000000000001,0.38400000000000001,0.50900000000000001,0.63400000000000001,0.75900000000000001}, {1,1,0,0,1});
bool valid=state.features<15>(1767225606700000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.95557916164398193,-0.26750952005386353,621.43902587890625,-118.81459045410156,9.0561666488647461,0,0,0,0,0,0,0,0.87038826942443848,0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225606700000000LL,out,valid)) return 4;
}
{
state.update(1767225606800000000LL, {0.26100000000000001,0.38600000000000001,0.51100000000000001,0.63600000000000001,0.76100000000000001}, {1,1,0,0,1});
bool valid=state.features<15>(1767225606800000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.95276260375976562,-0.26256400346755981,621.43902587890625,-118.81459045410156,9.0802497863769531,0,0,0,0,0,0,0,1.2185436487197876,1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225606800000000LL,out,valid)) return 4;
}
{
state.update(1767225606900000000LL, {0.26300000000000001,0.38800000000000001,0.51300000000000001,0.63800000000000001,0.76300000000000001}, {1,1,0,0,1});
bool valid=state.features<15>(1767225606900000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.94994598627090454,-0.2576184868812561,621.43902587890625,-118.81459045410156,9.1043338775634766,0,0,0,0,0,0,0,1.5666989088058472,1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225606900000000LL,out,valid)) return 4;
}
{
state.update(1767225607000000000LL, {0.26500000000000001,0.39000000000000001,0.51500000000000001,0.64000000000000001,0.76500000000000001}, {1,1,1,1,1});
bool valid=state.features<15>(1767225607000000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.94712936878204346,-0.25267300009727478,646.6348876953125,-118.80422973632812,9.12841796875,0,0,0,0,0,0,0,-1.5666989088058472,-1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225607000000000LL,out,valid)) return 4;
}
{
state.update(1767225607100000000LL, {0.26700000000000002,0.39200000000000002,0.51700000000000002,0.64200000000000002,0.76700000000000002}, {1,1,0,0,1});
bool valid=state.features<15>(1767225607100000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.94431281089782715,-0.24772748351097107,646.6348876953125,-118.80422973632812,9.152501106262207,0,0,0,0,0,0,0,-1.2185436487197876,-1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225607100000000LL,out,valid)) return 4;
}
{
state.update(1767225607200000000LL, {0.26900000000000002,0.39400000000000002,0.51900000000000002,0.64400000000000002,0.76900000000000002}, {1,1,0,0,1});
bool valid=state.features<15>(1767225607200000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.94149619340896606,-0.24278198182582855,646.6348876953125,-118.80422973632812,9.1765851974487305,0,0,0,0,0,0,0,-0.87038826942443848,-0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225607200000000LL,out,valid)) return 4;
}
{
state.update(1767225607300000000LL, {0.27100000000000002,0.39600000000000002,0.52100000000000002,0.64600000000000002,0.77100000000000002}, {1,1,0,0,1});
bool valid=state.features<15>(1767225607300000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.93867957592010498,-0.23783648014068604,646.6348876953125,-118.80422973632812,9.2006692886352539,0,0,0,0,0,0,0,-0.52223294973373413,-0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225607300000000LL,out,valid)) return 4;
}
{
state.update(1767225607400000000LL, {0.27300000000000002,0.39800000000000002,0.52300000000000002,0.64800000000000002,0.77300000000000002}, {1,1,0,0,1});
bool valid=state.features<15>(1767225607400000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.93586301803588867,-0.23289097845554352,646.6348876953125,-118.80422973632812,9.2247524261474609,0,0,0,0,0,0,0,-0.17407765984535217,-0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225607400000000LL,out,valid)) return 4;
}
{
state.update(1767225607500000000LL, {0.27500000000000002,0.40000000000000002,0.52500000000000002,0.65000000000000002,0.77500000000000002}, {1,1,0,0,1});
bool valid=state.features<15>(1767225607500000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.93304640054702759,-0.22794546186923981,646.6348876953125,-118.80422973632812,9.2488365173339844,0,0,0,0,0,0,0,0.17407765984535217,0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225607500000000LL,out,valid)) return 4;
}
{
state.update(1767225607600000000LL, {0.27700000000000002,0.40200000000000002,0.52700000000000002,0.65200000000000002,0.77700000000000002}, {1,1,0,0,1});
bool valid=state.features<15>(1767225607600000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.9302297830581665,-0.22299996018409729,646.6348876953125,-118.80422973632812,9.2729206085205078,0,0,0,0,0,0,0,0.52223294973373413,0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225607600000000LL,out,valid)) return 4;
}
{
state.update(1767225607700000000LL, {0.27900000000000003,0.40400000000000003,0.52900000000000003,0.65400000000000003,0.77900000000000003}, {1,1,0,0,1});
bool valid=state.features<15>(1767225607700000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.9274132251739502,-0.21805445849895477,646.6348876953125,-118.80422973632812,9.2970037460327148,0,0,0,0,0,0,0,0.87038826942443848,0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225607700000000LL,out,valid)) return 4;
}
{
state.update(1767225607800000000LL, {0.28100000000000003,0.40600000000000003,0.53100000000000003,0.65600000000000003,0.78100000000000003}, {1,1,0,0,1});
bool valid=state.features<15>(1767225607800000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.92459660768508911,-0.21310895681381226,646.6348876953125,-118.80422973632812,9.3210878372192383,0,0,0,0,0,0,0,1.2185436487197876,1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225607800000000LL,out,valid)) return 4;
}
{
state.update(1767225607900000000LL, {0.28300000000000003,0.40800000000000003,0.53300000000000003,0.65800000000000003,0.78300000000000003}, {1,1,0,0,1});
bool valid=state.features<15>(1767225607900000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.92177999019622803,-0.20816345512866974,646.6348876953125,-118.80422973632812,9.3451719284057617,0,0,0,0,0,0,0,1.5666989088058472,1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225607900000000LL,out,valid)) return 4;
}
{
state.update(1767225608000000000LL, {0.28500000000000003,0.41000000000000003,0.53500000000000003,0.66000000000000003,0.78500000000000003}, {2,1,1,1,1});
bool valid=state.features<15>(1767225608000000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != false) return 2; std::array<double,15> expected={-0.36089453101158142,-0.20321793854236603,671.8306884765625,-118.79386901855469,9.3692550659179688,1,0,0,0,0,0,0,-1.5666989088058472,-1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225608000000000LL,out,valid)) return 4;
}
{
state.update(1767225608100000000LL, {0.28700000000000003,0.41200000000000003,0.53700000000000003,0.66200000000000003,0.78700000000000003}, {2,1,0,0,1});
bool valid=state.features<15>(1767225608100000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != false) return 2; std::array<double,15> expected={-0.36089453101158142,-0.19827243685722351,671.8306884765625,-118.79386901855469,9.3933391571044922,1,0,0,0,0,0,0,-1.2185436487197876,-1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225608100000000LL,out,valid)) return 4;
}
{
state.update(1767225608200000000LL, {0.28900000000000003,0.41400000000000003,0.53900000000000003,0.66400000000000003,0.78900000000000003}, {2,1,0,0,1});
bool valid=state.features<15>(1767225608200000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != false) return 2; std::array<double,15> expected={-0.36089453101158142,-0.19332693517208099,671.8306884765625,-118.79386901855469,9.4174232482910156,1,0,0,0,0,0,0,-0.87038826942443848,-0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225608200000000LL,out,valid)) return 4;
}
{
state.update(1767225608300000000LL, {0.29100000000000004,0.41600000000000004,0.54100000000000004,0.66600000000000004,0.79100000000000004}, {2,1,0,0,1});
bool valid=state.features<15>(1767225608300000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != false) return 2; std::array<double,15> expected={-0.36089453101158142,-0.18838143348693848,671.8306884765625,-118.79386901855469,9.4415063858032227,1,0,0,0,0,0,0,-0.52223294973373413,-0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225608300000000LL,out,valid)) return 4;
}
{
state.update(1767225608400000000LL, {0.29300000000000004,0.41800000000000004,0.54300000000000004,0.66800000000000004,0.79300000000000004}, {1,1,0,0,1});
bool valid=state.features<15>(1767225608400000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.90769702196121216,-0.18343591690063477,671.8306884765625,-118.79386901855469,9.4655904769897461,0,0,0,0,0,0,0,-0.17407765984535217,-0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225608400000000LL,out,valid)) return 4;
}
{
state.update(1767225608500000000LL, {0.29500000000000004,0.42000000000000004,0.54500000000000004,0.67000000000000004,0.79500000000000004}, {1,1,0,0,1});
bool valid=state.features<15>(1767225608500000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.90488040447235107,-0.17849041521549225,671.8306884765625,-118.79386901855469,9.4896745681762695,0,0,0,0,0,0,0,0.17407765984535217,0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225608500000000LL,out,valid)) return 4;
}
{
state.update(1767225608600000000LL, {0.29700000000000004,0.42200000000000004,0.54700000000000004,0.67200000000000004,0.79700000000000004}, {1,1,0,0,1});
bool valid=state.features<15>(1767225608600000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.90206384658813477,-0.17354491353034973,671.8306884765625,-118.79386901855469,9.5137577056884766,0,0,0,0,0,0,0,0.52223294973373413,0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225608600000000LL,out,valid)) return 4;
}
{
state.update(1767225608700000000LL, {0.29900000000000004,0.42400000000000004,0.54900000000000004,0.67400000000000004,0.79900000000000004}, {1,1,0,0,1});
bool valid=state.features<15>(1767225608700000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.89924722909927368,-0.16859941184520721,671.8306884765625,-118.79386901855469,9.537841796875,0,0,0,0,0,0,0,0.87038826942443848,0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225608700000000LL,out,valid)) return 4;
}
{
state.update(1767225608800000000LL, {0.30099999999999999,0.42599999999999999,0.55099999999999993,0.67599999999999993,0.80099999999999993}, {1,1,0,0,1});
bool valid=state.features<15>(1767225608800000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.8964306116104126,-0.1636539101600647,671.8306884765625,-118.79386901855469,9.5619258880615234,0,0,0,0,0,0,0,1.2185436487197876,1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225608800000000LL,out,valid)) return 4;
}
{
state.update(1767225608900000000LL, {0.30299999999999999,0.42799999999999999,0.55299999999999994,0.67799999999999994,0.80299999999999994}, {1,1,0,0,1});
bool valid=state.features<15>(1767225608900000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.89361405372619629,-0.15870839357376099,671.8306884765625,-118.79386901855469,9.5860090255737305,0,0,0,0,0,0,0,1.5666989088058472,1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225608900000000LL,out,valid)) return 4;
}
{
state.update(1767225609000000000LL, {0.30499999999999999,0.42999999999999999,0.55499999999999994,0.67999999999999994,0.80499999999999994}, {1,1,1,1,1});
bool valid=state.features<15>(1767225609000000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.89079743623733521,-0.15376289188861847,697.02655029296875,-118.78350830078125,9.6100931167602539,0,0,0,0,0,0,0,-1.5666989088058472,-1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225609000000000LL,out,valid)) return 4;
}
{
state.update(1767225609100000000LL, {0.307,0.432,0.55699999999999994,0.68199999999999994,0.80699999999999994}, {1,1,0,0,1});
bool valid=state.features<15>(1767225609100000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.88798081874847412,-0.14881739020347595,697.02655029296875,-118.78350830078125,9.6341772079467773,0,0,0,0,0,0,0,-1.2185436487197876,-1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225609100000000LL,out,valid)) return 4;
}
{
state.update(1767225609200000000LL, {0.309,0.434,0.55899999999999994,0.68399999999999994,0.80899999999999994}, {1,1,0,0,1});
bool valid=state.features<15>(1767225609200000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.88516426086425781,-0.14387188851833344,697.02655029296875,-118.78350830078125,9.6582603454589844,0,0,0,0,0,0,0,-0.87038826942443848,-0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225609200000000LL,out,valid)) return 4;
}
{
state.update(1767225609300000000LL, {0.311,0.436,0.56099999999999994,0.68599999999999994,0.81099999999999994}, {1,1,0,0,1});
bool valid=state.features<15>(1767225609300000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.88234764337539673,-0.13892637193202972,697.02655029296875,-118.78350830078125,9.6823444366455078,0,0,0,0,0,0,0,-0.52223294973373413,-0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225609300000000LL,out,valid)) return 4;
}
{
state.update(1767225609400000000LL, {0.313,0.438,0.56299999999999994,0.68799999999999994,0.81299999999999994}, {1,1,0,0,1});
bool valid=state.features<15>(1767225609400000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.87953102588653564,-0.13398087024688721,697.02655029296875,-118.78350830078125,9.7064285278320312,0,0,0,0,0,0,0,-0.17407765984535217,-0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225609400000000LL,out,valid)) return 4;
}
{
state.update(1767225609500000000LL, {0.315,0.44,0.56499999999999995,0.68999999999999995,0.81499999999999995}, {1,1,0,0,1});
bool valid=state.features<15>(1767225609500000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.87671446800231934,-0.12903536856174469,697.02655029296875,-118.78350830078125,9.7305116653442383,0,0,0,0,0,0,0,0.17407765984535217,0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225609500000000LL,out,valid)) return 4;
}
{
state.update(1767225609600000000LL, {0.317,0.442,0.56699999999999995,0.69199999999999995,0.81699999999999995}, {1,1,0,0,1});
bool valid=state.features<15>(1767225609600000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.87389785051345825,-0.12408986687660217,697.02655029296875,-118.78350830078125,9.7545957565307617,0,0,0,0,0,0,0,0.52223294973373413,0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225609600000000LL,out,valid)) return 4;
}
{
state.update(1767225609700000000LL, {0.31900000000000001,0.44400000000000001,0.56899999999999995,0.69399999999999995,0.81899999999999995}, {1,1,0,0,1});
bool valid=state.features<15>(1767225609700000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.87108123302459717,-0.11914435774087906,697.02655029296875,-118.78350830078125,9.7786798477172852,0,0,0,0,0,0,0,0.87038826942443848,0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225609700000000LL,out,valid)) return 4;
}
{
state.update(1767225609800000000LL, {0.32100000000000001,0.44600000000000001,0.57099999999999995,0.69599999999999995,0.82099999999999995}, {1,1,0,0,1});
bool valid=state.features<15>(1767225609800000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.86826467514038086,-0.11419885605573654,697.02655029296875,-118.78350830078125,9.8027629852294922,0,0,0,0,0,0,0,1.2185436487197876,1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225609800000000LL,out,valid)) return 4;
}
{
state.update(1767225609900000000LL, {0.32300000000000001,0.44800000000000001,0.57299999999999995,0.69799999999999995,0.82299999999999995}, {1,1,0,0,1});
bool valid=state.features<15>(1767225609900000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.86544805765151978,-0.10925334692001343,697.02655029296875,-118.78350830078125,9.8268470764160156,0,0,0,0,0,0,0,1.5666989088058472,1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225609900000000LL,out,valid)) return 4;
}
{
state.update(1767225610000000000LL, {0.32500000000000001,0.45000000000000001,0.57499999999999996,0.69999999999999996,0.82499999999999996}, {1,1,1,1,1});
bool valid=state.features<15>(1767225610000000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.86263144016265869,-0.10430784523487091,722.22235107421875,-118.77314758300781,9.8509311676025391,0,0,0,0,0,0,0,-1.5666989088058472,-1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225610000000000LL,out,valid)) return 4;
}
{
state.update(1767225610100000000LL, {0.32700000000000001,0.45200000000000001,0.57699999999999996,0.70199999999999996,0.82699999999999996}, {1,1,0,0,1});
bool valid=state.features<15>(1767225610100000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.85981488227844238,-0.099362336099147797,722.22235107421875,-118.77314758300781,9.8750143051147461,0,0,0,0,0,0,0,-1.2185436487197876,-1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225610100000000LL,out,valid)) return 4;
}
{
state.update(1767225610200000000LL, {0.32900000000000001,0.45400000000000001,0.57899999999999996,0.70399999999999996,0.82899999999999996}, {1,1,0,0,1});
bool valid=state.features<15>(1767225610200000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.8569982647895813,-0.09441683441400528,722.22235107421875,-118.77314758300781,9.8990983963012695,0,0,0,0,0,0,0,-0.87038826942443848,-0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225610200000000LL,out,valid)) return 4;
}
{
state.update(1767225610300000000LL, {0.33100000000000002,0.45600000000000002,0.58099999999999996,0.70599999999999996,0.83099999999999996}, {1,1,0,0,1});
bool valid=state.features<15>(1767225610300000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.85418164730072021,-0.089471325278282166,722.22235107421875,-118.77314758300781,9.923182487487793,0,0,0,0,0,0,0,-0.52223294973373413,-0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225610300000000LL,out,valid)) return 4;
}
{
state.update(1767225610400000000LL, {0.33300000000000002,0.45800000000000002,0.58299999999999996,0.70799999999999996,0.83299999999999996}, {1,1,0,0,1});
bool valid=state.features<15>(1767225610400000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.85136508941650391,-0.084525823593139648,722.22235107421875,-118.77314758300781,9.947265625,0,0,0,0,0,0,0,-0.17407765984535217,-0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225610400000000LL,out,valid)) return 4;
}
{
state.update(1767225610500000000LL, {0.33499999999999996,0.45999999999999996,0.58499999999999996,0.70999999999999996,0.83499999999999996}, {1,1,0,0,1});
bool valid=state.features<15>(1767225610500000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.84854847192764282,-0.079580321907997131,722.22235107421875,-118.77314758300781,9.9713497161865234,0,0,0,0,0,0,0,0.17407765984535217,0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225610500000000LL,out,valid)) return 4;
}
{
state.update(1767225610600000000LL, {0.33699999999999997,0.46199999999999997,0.58699999999999997,0.71199999999999997,0.83699999999999997}, {1,1,0,0,1});
bool valid=state.features<15>(1767225610600000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.84573185443878174,-0.074634812772274017,722.22235107421875,-118.77314758300781,9.9954338073730469,0,0,0,0,0,0,0,0.52223294973373413,0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225610600000000LL,out,valid)) return 4;
}
{
state.update(1767225610700000000LL, {0.33899999999999997,0.46399999999999997,0.58899999999999997,0.71399999999999997,0.83899999999999997}, {1,1,0,0,1});
bool valid=state.features<15>(1767225610700000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.84291529655456543,-0.0696893110871315,722.22235107421875,-118.77314758300781,10.019516944885254,0,0,0,0,0,0,0,0.87038826942443848,0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225610700000000LL,out,valid)) return 4;
}
{
state.update(1767225610800000000LL, {0.34099999999999997,0.46599999999999997,0.59099999999999997,0.71599999999999997,0.84099999999999997}, {1,1,0,0,1});
bool valid=state.features<15>(1767225610800000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.84009867906570435,-0.064743801951408386,722.22235107421875,-118.77314758300781,10.043601036071777,0,0,0,0,0,0,0,1.2185436487197876,1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225610800000000LL,out,valid)) return 4;
}
{
state.update(1767225610900000000LL, {0.34299999999999997,0.46799999999999997,0.59299999999999997,0.71799999999999997,0.84299999999999997}, {1,1,0,0,1});
bool valid=state.features<15>(1767225610900000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.83728206157684326,-0.059798300266265869,722.22235107421875,-118.77314758300781,10.067685127258301,0,0,0,0,0,0,0,1.5666989088058472,1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225610900000000LL,out,valid)) return 4;
}
{
state.update(1767225611000000000LL, {0.34499999999999997,0.46999999999999997,0.59499999999999997,0.71999999999999997,0.84499999999999997}, {1,1,1,1,1});
bool valid=state.features<15>(1767225611000000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.83446550369262695,-0.054852794855833054,747.418212890625,-118.76278686523438,10.091768264770508,0,0,0,0,0,0,0,-1.5666989088058472,-1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225611000000000LL,out,valid)) return 4;
}
{
state.update(1767225611100000000LL, {0.34699999999999998,0.47199999999999998,0.59699999999999998,0.72199999999999998,0.84699999999999998}, {1,1,0,0,1});
bool valid=state.features<15>(1767225611100000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.83164888620376587,-0.049907289445400238,747.418212890625,-118.76278686523438,10.115852355957031,0,0,0,0,0,0,0,-1.2185436487197876,-1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225611100000000LL,out,valid)) return 4;
}
{
state.update(1767225611200000000LL, {0.34899999999999998,0.47399999999999998,0.59899999999999998,0.72399999999999998,0.84899999999999998}, {1,1,0,0,1});
bool valid=state.features<15>(1767225611200000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.82883226871490479,-0.044961784034967422,747.418212890625,-118.76278686523438,10.139936447143555,0,0,0,0,0,0,0,-0.87038826942443848,-0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225611200000000LL,out,valid)) return 4;
}
{
state.update(1767225611300000000LL, {0.35099999999999998,0.47599999999999998,0.60099999999999998,0.72599999999999998,0.85099999999999998}, {1,1,0,0,1});
bool valid=state.features<15>(1767225611300000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.82601571083068848,-0.040016278624534607,747.418212890625,-118.76278686523438,10.164019584655762,0,0,0,0,0,0,0,-0.52223294973373413,-0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225611300000000LL,out,valid)) return 4;
}
{
state.update(1767225611400000000LL, {0.35299999999999998,0.47799999999999998,0.60299999999999998,0.72799999999999998,0.85299999999999998}, {1,1,0,0,1});
bool valid=state.features<15>(1767225611400000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.82319909334182739,-0.035070773214101791,747.418212890625,-118.76278686523438,10.188103675842285,0,0,0,0,0,0,0,-0.17407765984535217,-0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225611400000000LL,out,valid)) return 4;
}
{
state.update(1767225611500000000LL, {0.35499999999999998,0.47999999999999998,0.60499999999999998,0.72999999999999998,0.85499999999999998}, {1,1,0,0,1});
bool valid=state.features<15>(1767225611500000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.82038247585296631,-0.030125267803668976,747.418212890625,-118.76278686523438,10.212187767028809,0,0,0,0,0,0,0,0.17407765984535217,0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225611500000000LL,out,valid)) return 4;
}
{
state.update(1767225611600000000LL, {0.35699999999999998,0.48199999999999998,0.60699999999999998,0.73199999999999998,0.85699999999999998}, {1,1,0,0,1});
bool valid=state.features<15>(1767225611600000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.81756591796875,-0.02517976425588131,747.418212890625,-118.76278686523438,10.236270904541016,0,0,0,0,0,0,0,0.52223294973373413,0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225611600000000LL,out,valid)) return 4;
}
{
state.update(1767225611700000000LL, {0.35899999999999999,0.48399999999999999,0.60899999999999999,0.73399999999999999,0.85899999999999999}, {1,1,0,0,1});
bool valid=state.features<15>(1767225611700000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.81474930047988892,-0.020234258845448494,747.418212890625,-118.76278686523438,10.260354995727539,0,0,0,0,0,0,0,0.87038826942443848,0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225611700000000LL,out,valid)) return 4;
}
{
state.update(1767225611800000000LL, {0.36099999999999999,0.48599999999999999,0.61099999999999999,0.73599999999999999,0.86099999999999999}, {1,1,0,0,1});
bool valid=state.features<15>(1767225611800000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.81193268299102783,-0.015288753435015678,747.418212890625,-118.76278686523438,10.284439086914062,0,0,0,0,0,0,0,1.2185436487197876,1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225611800000000LL,out,valid)) return 4;
}
{
state.update(1767225611900000000LL, {0.36299999999999999,0.48799999999999999,0.61299999999999999,0.73799999999999999,0.86299999999999999}, {1,1,0,0,1});
bool valid=state.features<15>(1767225611900000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.80911612510681152,-0.010343248955905437,747.418212890625,-118.76278686523438,10.30852222442627,0,0,0,0,0,0,0,1.5666989088058472,1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225611900000000LL,out,valid)) return 4;
}
{
state.update(1767225612000000000LL, {0.36499999999999999,0.48999999999999999,0.61499999999999999,0.73999999999999999,0.86499999999999999}, {1,1,1,1,1});
bool valid=state.features<15>(1767225612000000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.80629950761795044,-0.0053977435454726219,772.614013671875,-118.75242614746094,10.332606315612793,0,0,0,0,0,0,0,-1.5666989088058472,-1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225612000000000LL,out,valid)) return 4;
}
{
state.update(1767225612100000000LL, {0.36699999999999999,0.49199999999999999,0.61699999999999999,0.74199999999999999,0.86699999999999999}, {1,1,0,0,1});
bool valid=state.features<15>(1767225612100000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.80348289012908936,-0.00045223874622024596,772.614013671875,-118.75242614746094,10.356690406799316,0,0,0,0,0,0,0,-1.2185436487197876,-1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225612100000000LL,out,valid)) return 4;
}
{
state.update(1767225612200000000LL, {0.36899999999999999,0.49399999999999999,0.61899999999999999,0.74399999999999999,0.86899999999999999}, {1,1,0,0,1});
bool valid=state.features<15>(1767225612200000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.80066633224487305,0.0044932663440704346,772.614013671875,-118.75242614746094,10.380773544311523,0,0,0,0,0,0,0,-0.87038826942443848,-0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225612200000000LL,out,valid)) return 4;
}
{
state.update(1767225612300000000LL, {0.371,0.496,0.621,0.746,0.871}, {1,1,0,0,1});
bool valid=state.features<15>(1767225612300000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.79784971475601196,0.0094387708231806755,772.614013671875,-118.75242614746094,10.404857635498047,0,0,0,0,0,0,0,-0.52223294973373413,-0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225612300000000LL,out,valid)) return 4;
}
{
state.update(1767225612400000000LL, {0.373,0.498,0.623,0.748,0.873}, {1,1,0,0,1});
bool valid=state.features<15>(1767225612400000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.79503309726715088,0.014384276233613491,772.614013671875,-118.75242614746094,10.42894172668457,0,0,0,0,0,0,0,-0.17407765984535217,-0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225612400000000LL,out,valid)) return 4;
}
{
state.update(1767225612500000000LL, {0.375,0.5,0.625,0.75,0.875}, {1,1,0,0,1});
bool valid=state.features<15>(1767225612500000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.79221653938293457,0.019329780712723732,772.614013671875,-118.75242614746094,10.453024864196777,0,0,0,0,0,0,0,0.17407765984535217,0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225612500000000LL,out,valid)) return 4;
}
{
state.update(1767225612600000000LL, {0.377,0.502,0.627,0.752,0.877}, {1,1,0,0,1});
bool valid=state.features<15>(1767225612600000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.78939992189407349,0.024275286123156548,772.614013671875,-118.75242614746094,10.477108955383301,0,0,0,0,0,0,0,0.52223294973373413,0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225612600000000LL,out,valid)) return 4;
}
{
state.update(1767225612700000000LL, {0.379,0.504,0.629,0.754,0.879}, {1,1,0,0,1});
bool valid=state.features<15>(1767225612700000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.7865833044052124,0.029220791533589363,772.614013671875,-118.75242614746094,10.501193046569824,0,0,0,0,0,0,0,0.87038826942443848,0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225612700000000LL,out,valid)) return 4;
}
{
state.update(1767225612800000000LL, {0.38100000000000001,0.50600000000000001,0.63100000000000001,0.75600000000000001,0.88100000000000001}, {1,1,0,0,1});
bool valid=state.features<15>(1767225612800000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.78376674652099609,0.034166295081377029,772.614013671875,-118.75242614746094,10.525276184082031,0,0,0,0,0,0,0,1.2185436487197876,1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225612800000000LL,out,valid)) return 4;
}
{
state.update(1767225612900000000LL, {0.38300000000000001,0.50800000000000001,0.63300000000000001,0.75800000000000001,0.88300000000000001}, {1,1,0,0,1});
bool valid=state.features<15>(1767225612900000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.78095012903213501,0.039111800491809845,772.614013671875,-118.75242614746094,10.549360275268555,0,0,0,0,0,0,0,1.5666989088058472,1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225612900000000LL,out,valid)) return 4;
}
{
state.update(1767225613000000000LL, {0.38500000000000001,0.51000000000000001,0.63500000000000001,0.76000000000000001,0.88500000000000001}, {1,1,1,1,1});
bool valid=state.features<15>(1767225613000000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.77813351154327393,0.044057305902242661,797.80987548828125,-118.7420654296875,10.573444366455078,0,0,0,0,0,0,0,-1.5666989088058472,-1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225613000000000LL,out,valid)) return 4;
}
{
state.update(1767225613100000000LL, {0.38700000000000001,0.51200000000000001,0.63700000000000001,0.76200000000000001,0.88700000000000001}, {1,1,0,0,1});
bool valid=state.features<15>(1767225613100000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.77531695365905762,0.049002811312675476,797.80987548828125,-118.7420654296875,10.597527503967285,0,0,0,0,0,0,0,-1.2185436487197876,-1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225613100000000LL,out,valid)) return 4;
}
{
state.update(1767225613200000000LL, {0.38900000000000001,0.51400000000000001,0.63900000000000001,0.76400000000000001,0.88900000000000001}, {1,1,0,0,1});
bool valid=state.features<15>(1767225613200000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.77250033617019653,0.053948316723108292,797.80987548828125,-118.7420654296875,10.621611595153809,0,0,0,0,0,0,0,-0.87038826942443848,-0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225613200000000LL,out,valid)) return 4;
}
{
state.update(1767225613300000000LL, {0.39100000000000001,0.51600000000000001,0.64100000000000001,0.76600000000000001,0.89100000000000001}, {1,1,0,0,1});
bool valid=state.features<15>(1767225613300000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.76968371868133545,0.058893822133541107,797.80987548828125,-118.7420654296875,10.645695686340332,0,0,0,0,0,0,0,-0.52223294973373413,-0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225613300000000LL,out,valid)) return 4;
}
{
state.update(1767225613400000000LL, {0.39300000000000002,0.51800000000000002,0.64300000000000002,0.76800000000000002,0.89300000000000002}, {1,1,0,0,1});
bool valid=state.features<15>(1767225613400000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.76686716079711914,0.063839323818683624,797.80987548828125,-118.7420654296875,10.669778823852539,0,0,0,0,0,0,0,-0.17407765984535217,-0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225613400000000LL,out,valid)) return 4;
}
{
state.update(1767225613500000000LL, {0.39500000000000002,0.52000000000000002,0.64500000000000002,0.77000000000000002,0.89500000000000002}, {1,1,0,0,1});
bool valid=state.features<15>(1767225613500000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.76405054330825806,0.068784832954406738,797.80987548828125,-118.7420654296875,10.693862915039062,0,0,0,0,0,0,0,0.17407765984535217,0.17407765984535217,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225613500000000LL,out,valid)) return 4;
}
{
state.update(1767225613600000000LL, {0.39700000000000002,0.52200000000000002,0.64700000000000002,0.77200000000000002,0.89700000000000002}, {1,1,0,0,1});
bool valid=state.features<15>(1767225613600000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.76123392581939697,0.073730334639549255,797.80987548828125,-118.7420654296875,10.717947006225586,0,0,0,0,0,0,0,0.52223294973373413,0.52223294973373413,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225613600000000LL,out,valid)) return 4;
}
{
state.update(1767225613700000000LL, {0.39900000000000002,0.52400000000000002,0.64900000000000002,0.77400000000000002,0.89900000000000002}, {1,1,0,0,1});
bool valid=state.features<15>(1767225613700000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.75841736793518066,0.078675843775272369,797.80987548828125,-118.7420654296875,10.742030143737793,0,0,0,0,0,0,0,0.87038826942443848,0.87038826942443848,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225613700000000LL,out,valid)) return 4;
}
{
state.update(1767225613800000000LL, {0.40100000000000002,0.52600000000000002,0.65100000000000002,0.77600000000000002,0.90100000000000002}, {1,1,0,0,1});
bool valid=state.features<15>(1767225613800000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.75560075044631958,0.083621345460414886,797.80987548828125,-118.7420654296875,10.766114234924316,0,0,0,0,0,0,0,1.2185436487197876,1.2185436487197876,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225613800000000LL,out,valid)) return 4;
}
{
state.update(1767225613900000000LL, {0.40300000000000002,0.52800000000000002,0.65300000000000002,0.77800000000000002,0.90300000000000002}, {1,1,0,0,1});
bool valid=state.features<15>(1767225613900000000LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);
if(valid != true) return 2; std::array<double,15> expected={-0.7527841329574585,0.088566854596138,797.80987548828125,-118.7420654296875,10.79019832611084,0,0,0,0,0,0,0,1.5666989088058472,1.5666989088058472,0};
for(std::size_t j=0;j<15;++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;
if(!ring.append(1767225613900000000LL,out,valid)) return 4;
}
std::array<float,960> seq; if(ring.latest<64>(seq.data(),100000000LL)) return 5;
lightning::Decision decision(.7,.4,2); if(decision.update(.8,true).alarm) return 6; if(!decision.update(.8,true).alarm) return 7; if(!decision.update(0,false).alarm) return 8; if(decision.update(.2,true).alarm) return 9;
std::cout << "{\"ring_sizeof_bytes\":" << sizeof(ring) << ",\"golden_vectors\":140}"; return 0;}
