function [E,varargout]=calc_eotvos_full(lat,lon,ht,datarate,a,ecc)
%function [E,varargout]=calc_eotvos_full(t,lat,lon,ht,a,b)
% program calc_eotvos_full calculates the complete 
%formulation of the eotvos correction from Harlan 1968
%
%USAGE: 
%   E=calc_eotvos_full(t,lat,lon,ht,a,ecc);
%   E=calc_eotvos_full(t,lat,lon,ht);
%   [E,rdd,aacc,cor,cent,cente]=calc_eotvos_full(...);
%
%INPUT assumed to be row vectors
%   lat     ARRAY   geodetic latitude in decimal degrees
%   lon    ARRAY   longitude in decimal degrees
%   ht      ARRAY  ellipsoidal height m
%   datarate Scalar data rate in Hz
%   a       Scalar     semi-major axis of ellipsoid, meters
%   ecc       Scalar     eccentricity of ellipsoid
%
%OUTPUT
%   E   ARRAY of eotvos values in mgals
%   componants of E in this order:
%       rdoubledot
%       angular acceloration of the reference frame
%       coriolis
%       centrifugal
%       centrifugal acc of earth
%
%Ref: Harlan 1968, "Eotvos Corrections for Airborne Gravimetry" JGR 73,n14
%
%Created by Sandra Preaux, NGS, NOAA August 24, 2009
%Modified to use 10th order Taylor derivative from micro-g SP Feb 2010
%reverted to central difference derivative (due to superior performance on
%   a noisy signal) and modified for use in DGS Eotvos software, including
%   column/row checking September 2015 SAMP
%Modified to use a and ecc instead of a, b as ellipsoid parameters Oct 2015 SAMP
%Modified to import datarate instead of t Oct 2015 SAMP

%if iscolumn(t)
%    t=t';
%end
if iscolumn(lat)
    lat=lat';
end
if iscolumn(lon)
    lon=lon';
end
if iscolumn(ht)
    ht=ht';
end

%define constants
if nargin<6
    a=6378137.0;    %default semi-major axis
    b=6356752.3142; %default semi-minor axis
    ecc=(a-b)/a;  %eccentricity
end
We=0.00007292115;    %siderial rotation rate, radians/sec
mps2mgal=100000; %m/s/s to mgal

%convert degrees to radians
latr=deg2rad(lat);
lonr=deg2rad(lon);

%find data rate
%dt=mode(diff(t));
%datarate=1/dt;  %Hz

%get derivitives of position
 dlat=d(latr,1,datarate);
 ddlat=d(latr,2,datarate);
 dlon=d(lonr,1,datarate);
 ddlon=d(lonr,2,datarate);
 dht=d(ht,1,datarate);
 ddht=d(ht,2,datarate);

%calculate sin(lat), cos(lat), sin(2*lat) and cos(2*lat) 
sinlat=sin(latr(2:end-1));
coslat=cos(latr(2:end-1));
sin2lat=sin(2.0.*latr(2:end-1));
cos2lat=cos(2.0.*latr(2:end-1));

%calculate the r' and its derivatives
rp=a.*(1-ecc.*sinlat.*sinlat);
drp=-a.*dlat.*ecc.*sin2lat;
ddrp=-a.*ddlat.*ecc.*sin2lat-2.0.*a.*dlat.*dlat.*ecc.*cos2lat;

%calculate the deviation from the normal and derivatives
D=atan(ecc.*sin2lat);
dD=2.0.*dlat.*ecc.*cos2lat;
ddD=2.0.*ddlat.*ecc.*cos2lat - 4.0.*dlat.*dlat.*ecc.*sin2lat;
   
%define r and it's derivatives
r=[-rp.*sin(D);zeros(size(rp));(-rp.*cos(D)-ht(2:(end-1)))];
rdot=[(-drp.*sin(D)-rp.*dD.*cos(D));zeros(size(rp));(-drp.*cos(D)+rp.*dD.*sin(D)-dht)];
ci=(-ddrp.*sin(D)-2.0.*drp.*dD.*cos(D)-rp.*(ddD.*cos(D)-dD.*dD.*sin(D)));
ck=(-ddrp.*cos(D)+2.0.*drp.*dD.*sin(D)+rp.*(ddD.*sin(D)+dD.*dD.*cos(D))-ddht);
rdotdot=[ci;zeros(size(ci));ck];

%define w and derivitive
w=[(dlon+We).*coslat;-dlat;(-(dlon+We).*sinlat)];
wdot=[(dlon.*coslat-(dlon+We).*dlat.*sinlat);-ddlat;(-ddlon.*sinlat-(dlon+We).*dlat.*coslat)];

w2xrdot=cross(2.0.*w,rdot);
wdotxr=cross(wdot,r);
wxr=cross(w,r);
wxwxr=cross(w,wxr);

%calculate wexwexre, that is the centrifugal acceloration due to the earth
re=[-rp.*sin(D);zeros(size(rp));-rp.*cos(D)];
we=[We.*coslat;zeros(size(sinlat));-We.*sinlat];
wexre=cross(we,re);
wexwexre=cross(we,wexre);
wexr=cross(we,r);
wexwexr=cross(we,wexr);


%calculate total acceloration for the aircraft
a=rdotdot+w2xrdot+wdotxr+wxwxr;

%Eotvos correction is vertical componant of the total acceloration of 
%the aircraft - the centrifugal acceloration of the earth, converted to
%mgal
E=(a(3,:)-wexwexr(3,:)).*mps2mgal;
E=[E(1) E E(end)]; %fill ends due to loss durring derivative computaion
if nargout>1
    terms{1}=rdotdot;
    terms{2}=w2xrdot;
    terms{3}=wdotxr;
    terms{4}=wxwxr;
    terms{5}=wexwexr;
    varargout=terms;
end