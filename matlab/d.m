function dy=d(y,n,datarate)
% Function to numerically estimate the nth time derivative of y
% Usage: dy=d(y,n,datarate);
% note n can have values of 1 or 2
% in both cases length(dy)=length(y)-2, one element from each end is lost

% Created August 2001 by Sandra Martinka

L=length(y);

switch n
case 1
  dy=(y(3:L)-y(1:(L-2))).*(datarate/2);
case 2
  dy=(y(1:(L-2))-2.*y(2:(L-1))+y(3:L)).*(datarate^2);
otherwise
  disp(['the ',n,'th derivative not supported.']);
end