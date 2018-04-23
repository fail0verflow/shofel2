
$fn=30;

w=9.1;
w2=w-2;

pp=0.65;
pw=0.4;
pins=10;
ps=((pins-1)*pp+pw)/2;
pl=4.5;
ph=0.6;

hl=11;
hw=3.4;
hpw=4*pp+pw;
hdh=ph-0.2;
pl2=3.5;

union() {
    difference() {
        union() {
            cube([w,20,1.8]);
            translate([1,4.5,0])
                cube([w2,15.5,3]);
        }
        translate([(w-w2)/2,0,0.8])
            cube([w2,4.5,1.8]);
        for (pin = [0:pins-1]) {
            translate([w/2-ps+pin*pp,0,ph])
                cube([pw,pl,2]);
        }
        translate([w/2+ps-hw+(hw-hpw)/2,pl2,hdh])
            cube([hw, hl-pl2, 4]);
    }
    translate([w/2,15,3])
        cylinder(2, 2.5, 2.5);
}
