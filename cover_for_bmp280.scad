op=28;
oh=10;
wt=1.5;

$fn=50;

union() {
difference() {
    union() {
      minkowski() {
        cube([op-2, op-2, oh-3], center=true);
        cylinder(1,1);
      }
      translate([0, 0, wt]) {
        cube([op-2.2, op-2.2, oh], center=true);
      }
    }
    translate([0, 0, wt*2]) {
      cube([op-3, op-3, oh], center=true);
    }
    translate([0, 5.5, wt*2]) {
      cube([30, 8, 10], center=true);
    }
}

translate([7, -wt, wt]) {
  cylinder(7, 1.3, 1.3, center=true);
}

translate([-7, -wt, wt]) {
  cylinder(7, 1.3, 1.3, center=true);
}
}


difference() {
translate([40, 0, -2.5]) {
  difference() {
    minkowski() {
      cube([op-2, op-2,2], center=true);
      cylinder(1,1);
    }
    translate([0, 0, 1.5]) {
      cube([op-2, op-2, 3], center=true);
    }
  }
}

for (i = [1:1:6]) {
  for (j = [1:1:6]) {
    translate([25.25 + j*4.2, -14.75 + i*4.2, -2.5]) {
      cylinder(6, 1.9, center=true);
    }
  }
}
}
